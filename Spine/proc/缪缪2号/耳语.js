/* 缪缪2号 · 耳语（凑到对方耳边：一手挡嘴，交头接耳）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["耳语"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 前倾凑近，说悄悄话时身体一点一点
      root.rotation += 12 + 2.5 * S(3 * t);
      root.scaleY = 1 - 0.025 * Math.abs(S(3 * t));
      // 一手挡在嘴边，另一只手背在身后
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (al) al.rotation += 68 + 5 * S(6 * t);
      if (fl) fl.rotation += 92 + 6 * S(6 * t);
      if (ar) ar.rotation += 42;
      if (fr) fr.rotation += -26;
      var head = g('F_Head');
      if (head) head.rotation += -7 + 3 * S(3 * t);
      var anch = head || root;
      topFx(fx, 'whis1', anch, 40, -70, 0.85, '🤫');
      topFx(fx, 'whis2', anch, -44, -52, 0.35 + 0.3 * Math.abs(S(2 * t)), '💬');
    }
  };
})();
