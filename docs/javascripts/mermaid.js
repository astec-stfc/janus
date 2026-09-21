document$.subscribe(({ body }) => {
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: document.body.getAttribute("data-md-color-scheme") === "slate"
      ? "dark"
      : "default",
  });

  mermaid.run({
    nodes: body.querySelectorAll(".mermaid"),
  });
});
