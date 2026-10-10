// 好用例 sw.js：MV3 service worker 规范写法
// 注意：service worker 无 DOM 环境，不用 document/window；
// 定时任务不用 setInterval，用 chrome.alarms（SW 会被浏览器休眠）。
chrome.runtime.onInstalled.addListener(function () {
  chrome.alarms.create("daily", { periodInMinutes: 60 * 24 });
});

chrome.alarms.onAlarm.addListener(function (alarm) {
  if (alarm.name === "daily") {
    chrome.storage.local.get(["count"], function (data) {
      chrome.storage.local.set({ count: (data.count || 0) + 1 });
    });
  }
});

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  if (msg.type === "ping") {
    sendResponse({ type: "pong" });
  }
  return false;
});
