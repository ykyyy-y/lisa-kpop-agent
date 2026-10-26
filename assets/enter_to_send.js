// Enter sends the message, Shift+Enter adds a new line.
document.addEventListener("keydown", function (e) {
  const box = document.getElementById("chat-input");
  if (!box || e.target !== box) return;
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    const btn = document.getElementById("send-btn");
    if (btn && !btn.disabled) btn.click();
  }
});

// Keep the newest message in view.
new MutationObserver(function () {
  const box = document.getElementById("messages");
  if (box) box.scrollTop = box.scrollHeight;
}).observe(document.documentElement, { childList: true, subtree: true });
