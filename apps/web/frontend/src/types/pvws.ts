export type AlarmSeverity = "NO_ALARM" | "MINOR" | "MAJOR" | "INVALID";

export interface NTEnum {
  index: number;
  choices?: string[];
}

export type PVValue =
  | number
  | string
  | number[]
  | string[]
  | NTEnum
  | undefined;

// SERVER -> CLIENT MESSAGES (messages the server sends to us)

export interface UpdateMessage {
  type: "update";
  pv: string;
  value?: PVValue;
  readonly?: boolean;
  seconds?: number;
  nanos?: number;
  vtype?: string; // not from the norm types, but from pvws
  units?: string;
  status?: string;
  precision?: number;
  min?: number;
  max?: number;
  warn_low?: number;
  warn_high?: number;
  alarm_low?: number;
  alarm_high?: number;
  labels?: string[];
  text?: string;
  severity?: AlarmSeverity;
}

export interface ErrorMessage {
  type: "error";
  pv?: string;
  message: string;
}

export interface ListMessage {
  type: "list";
  pvs: string[];
}

export interface PongMessage {
  type: "pong";
}

export type ServerMessage =
  | UpdateMessage
  | ErrorMessage
  | ListMessage
  | PongMessage;

// CLIENT -> SERVER MESSAGES (messages we send to the server)

export interface SubscribeMessage {
  type: "subscribe";
  pvs: string[];
}

export interface ClearMessage {
  type: "clear";
  pvs: string[];
}

export interface WriteMessage {
  type: "write";
  pv: string;
  value: string | number;
}

export interface PingMessage {
  type: "ping";
}

export interface RequestListMessage {
  type: "list";
}

export type ClientMessage =
  | SubscribeMessage
  | ClearMessage
  | WriteMessage
  | PingMessage
  | RequestListMessage;
