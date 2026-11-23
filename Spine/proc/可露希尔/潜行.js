/* 可露希尔 · 潜行（去找内幕：猫着腰贴墙走，边走边左右张望）
 * 叠在官方 Move 之上：弓背缩身 + 探头张望 + 手臂背在身后。
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
  window.PROCS["潜行"] = {
    base: "Move",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 弓背缩身（前倾 + 压低），踮脚弹跳
      root.rotation += 15 + 2.5 * S(7 * t);
      root.scaleY = 0.91 + 0.025 * Math.abs(S(7 * t));
      root.scaleX = 1 + 0.025 * Math.abs(S(7 * t));
      // 探头左右张望（比走路节奏慢）
      var head = g('F_Head_I');
      if (head) head.rotation += 30 * S(1.4 * t);
      // 手臂背在身后（抬手的反号）
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += 24;
      if (ar) ar.rotation += -24;
      if (fl) fl.rotation += 18;
      if (fr) fr.rotation += -18;
      var anch = head || root;
      topFx(fx, 'sneak1', anch, -44, -66, 0.45 + 0.35 * Math.abs(S(1.4 * t)), '👀');
    }
  };
})();
