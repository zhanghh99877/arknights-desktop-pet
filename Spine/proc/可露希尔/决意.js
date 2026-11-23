/* 可露希尔 · 决意（复盘完得出结论：搓手，眼神从💡变成😏）
 * 坐姿之上叠加：来回搓手 + 身体前倾 + 头微歪；💡渐隐、😏渐显。
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
  window.PROCS["决意"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 前倾凑近，头一歪
      root.rotation += 6;
      root.scaleY = 1 + 0.02 * S(4 * t);
      var head = g('F_Head_I');
      if (head) head.rotation += 5 + 2 * S(4 * t);
      // 来回搓手：小臂反相快速搓
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -26;
      if (ar) ar.rotation += 26;
      if (fl) fl.rotation += -30 - 26 * S(8 * t);
      if (fr) fr.rotation += 30 - 26 * S(8 * t + Math.PI);
      // 腿尖点地打拍子
      var cl = g('F_L_Calf_I'), cr = g('F_R_Calf_I');
      if (cl) cl.rotation += 6 * S(4 * t);
      if (cr) cr.rotation += -6 * S(4 * t + 0.5);
      var anch = head || root;
      topFx(fx, 'idea', anch, -46, -86, Math.max(0, 0.9 - t / 3), '💡');
      topFx(fx, 'smirk', anch, 42, -58, Math.min(0.95, 0.25 + t / 3), '😏');
    }
  };
})();
