// 坏用例 content.js：故意埋点
(function () {
  // 埋点: eval → BE-SEC-001
  var cfg = eval('(' + '{"color": "red"}' + ')');
  // 埋点: innerHTML → BE-SEC-002
  document.body.innerHTML = '<div>' + location.href + '</div>';
})();
