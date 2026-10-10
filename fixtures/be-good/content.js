// 好用例 content.js：在目标页面上加一个悬浮按钮
(function () {
  "use strict";
  var btn = document.createElement("button");
  btn.textContent = "示例插件";
  btn.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:999999;";
  btn.addEventListener("click", function () {
    chrome.runtime.sendMessage({ type: "ping" }, function (resp) {
      btn.textContent = "pong:" + (resp && resp.type === "pong");
    });
  });
  document.body.appendChild(btn);
})();
