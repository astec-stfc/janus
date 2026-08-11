import { toByteArray } from "base64-js";
import type {
  ServerMessage,
  UpdateMessage,
  SubscribeMessage,
  ClearMessage,
  WriteMessage,
  PingMessage,
  RequestListMessage,
} from "@/types/pvws";

class PVWS {
  private url: string;
  private connect_handler: (connected: boolean) => void;
  private message_handler: (message: ServerMessage) => void;
  private idle: boolean = true;
  private idle_timer: ReturnType<typeof setInterval> | null = null;
  private values: Record<string, UpdateMessage> = {};
  private intentional_close: boolean = false;
  public socket: WebSocket | null = null;

  // Attempt re-connect after 10 seconds
  private reconnect_ms: number = 10000;
  // Perform idle check every 5 minutes
  private idle_check_ms: number = 300000;

  /** Create PV Web Socket
   *
   *  <p>Message handler will be called with 'update'
   *  or 'error' message.
   *  The 'update' will contain the complete PV value,
   *  i.e. the merge of last known value and actual update.
   *
   *  @param url URL of the PV web socket, e.g. "ws://localhost:8080/pvws/pv"
   *  @param connect_handler Called with true/false when connected/disconnected
   *  @param message_handler Called with each received message
   */
  constructor(
    url: string,
    connect_handler: (connected: boolean) => void,
    message_handler: (message: ServerMessage) => void,
  ) {
    this.url = url;
    this.connect_handler = connect_handler;
    this.message_handler = message_handler;

    // In local tests, the web socket tends to stay open indefinitely,
    // but in production setups with proxies etc. they often time out
    // after about a minute of inactivity.
    // The server side could periodically 'ping' from the SessionManager,
    // or the client could send periodic 'echo' messages.
    // We combine both approaches by having the client send ping requests
    // when the connection is idle. The server will then issue the ping,
    // and the client should return a pong (but there's no way to see that ping/pong in javascript).
  }

  /** Open the web socket, i.e. start PV communication */
  open(): void {
    this.intentional_close = false;
    // upon opening set state to false -> but maybe we can use a `null` to indicate "Awaiting" or something..
    this.connect_handler(false);
    console.log("Opening " + this.url);
    this.socket = new WebSocket(this.url);
    this.socket.onopen = () => this.handleConnection();
    this.socket.onmessage = (event) => this.handleMessage(event.data);
    this.socket.onclose = (event) => this.handleClose(event);
    this.socket.onerror = (event) => this.handleError(event);
  }

  private handleConnection(): void {
    console.log("Connected to " + this.url);
    this.connect_handler(true);

    // Start idle check
    if (this.idle_timer == null)
      this.idle_timer = setInterval(
        () => this.checkIdleTimeout(),
        this.idle_check_ms,
      );
  }

  private checkIdleTimeout(): void {
    if (this.idle) {
      // console.log("Idle connection " + this.url);
      this.ping();
    } else {
      // console.log("Active connection " + this.url);
      // Reset to detect new messages
      this.idle = true;
    }
  }

  private stopIdleCheck(): void {
    if (this.idle_timer != null) clearInterval(this.idle_timer);
    this.idle_timer = null;
  }

  private handleMessage(message: string): void {
    // console.log("Received Message: " + message);
    this.idle = false;
    let jm = JSON.parse(message) as any;

    if (jm.type === "update") {
      // Decode binary
      // TODO Assert that we always use LITTLE_ENDIAN
      if (jm.b64dbl !== undefined) {
        let bytes = toByteArray(jm.b64dbl);
        jm.value = new Float64Array(bytes.buffer);
        // Convert to plain array
        // When keeping the Float64Array, the JSON representation
        // will be [ "0": val0, "1": val1, ... ]
        // instead of plain array [ val0, val1, ... ]
        jm.value = Array.prototype.slice.call(jm.value);
        // console.log(jm.value);
        // console.log(JSON.stringify(jm.value));
        delete jm.b64dbl;
      } else if (jm.b64flt !== undefined) {
        let bytes = toByteArray(jm.b64flt);
        jm.value = new Float32Array(bytes.buffer);
        // Convert to plain array
        jm.value = Array.prototype.slice.call(jm.value);
        delete jm.b64flt;
      } else if (jm.b64srt !== undefined) {
        let bytes = toByteArray(jm.b64srt);
        jm.value = new Int16Array(bytes.buffer);
        // Convert to plain array, if necessary
        jm.value = Array.prototype.slice.call(jm.value);
        delete jm.b64srt;
      } else if (jm.b64int !== undefined) {
        let bytes = toByteArray(jm.b64int);
        jm.value = new Int32Array(bytes.buffer);
        // Convert to plain array, if necessary
        jm.value = Array.prototype.slice.call(jm.value);
        delete jm.b64int;
      } else if (jm.b64byt !== undefined) {
        let bytes = toByteArray(jm.b64byt);
        jm.value = new Uint8Array(bytes.buffer);
        // Convert to plain array, if necessary
        jm.value = Array.prototype.slice.call(jm.value);
        delete jm.b64byt;
      }

      // Merge received data with last known value
      let value = this.values[jm.pv];
      // No previous value:
      // Default to read-only, no data
      if (value === undefined)
        value = { pv: jm.pv, readonly: true } as UpdateMessage;

      // Update cached value with received changes
      Object.assign(value, jm);
      if (value.vtype === "VString" && typeof value.text === "string") {
        value.value = value.text;
      }
      this.values[jm.pv] = value;
      // console.log("Update for PV " + jm.pv + ": " + JSON.stringify(value));
      this.message_handler(value);
    } else {
      this.message_handler(jm as ServerMessage);
    }
  }

  private handleError(event: Event): void {
    console.error("Error from " + this.url);
    console.error(event);
    this.close();
  }

  private handleClose(event: CloseEvent): void {
    this.stopIdleCheck();
    this.connect_handler(false);
    let message = "Web socket closed (" + event.code;
    if (event.reason) message += ", " + event.reason;
    message += ")";
    console.log(message);

    // Only reconnect if not intentionally closed
    if (!this.intentional_close) {
      console.log(
        `Attempting reconnect to ${this.url} in ${this.reconnect_ms} ms`,
      );
      setTimeout(() => this.open(), this.reconnect_ms);
    }
  }

  /** Ask server to ping this web socket,
   *  whereupon most web clients would then reply with a 'pong'
   *  back to the server.
   */
  ping(): void {
    console.log("Sending ping to " + this.url);
    const message: PingMessage = { type: "ping" };
    this.socket?.send(JSON.stringify(message));
  }

  /** Subscribe to one or more PVs
   *  @param pvs PV name or array of PV names
   */
  subscribe(pvs: string | string[]): void {
    const pvArray = Array.isArray(pvs) ? pvs : [pvs];
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message: SubscribeMessage = { type: "subscribe", pvs: pvArray };
      this.socket.send(JSON.stringify(message));
    }
  }

  /** Un-Subscribe from one or more PVs
   *  @param pvs PV name or array of PV names
   */
  clear(pvs: string | string[]): void {
    const pvArray = Array.isArray(pvs) ? pvs : [pvs];
    const message: ClearMessage = { type: "clear", pvs: pvArray };
    this.socket?.send(JSON.stringify(message));

    // Remove entry for cleared PVs from this.values
    for (const pv of pvArray) {
      delete this.values[pv];
    }
  }

  /** Request list of PVs */
  list(): void {
    const message: RequestListMessage = { type: "list" };
    this.socket?.send(JSON.stringify(message));
  }

  /** Write to PV
   *  @param pv PV name
   *  @param value number or string
   */
  write(pv: string, value: string | number): void {
    const message: WriteMessage = { type: "write", pv, value };
    this.socket?.send(JSON.stringify(message));
  }

  /** Close the web socket.
   *
   *  <p>Socket will automatically re-open,
   *  similar to handling an error.
   */
  close(): void {
    this.intentional_close = true;
    this.stopIdleCheck();
    // Only close if socket is OPEN (readyState === 1)
    // Closing a CONNECTING socket causes warnings
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
    }
  }
}

export default PVWS;
