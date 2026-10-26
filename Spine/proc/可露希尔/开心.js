/* 可露希尔 · 开心（涨停日彩蛋动作）
 * 坐姿之上叠加：大幅压扁拉伸 + 双臂高举挥舞 + 踢腿 + 欢呼特效。
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
  window.PROCS["开心"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      var b = Math.abs(S(7 * t));
      root.scaleY = 1 + 0.20 * b;
      root.scaleX = 1 - 0.12 * b;
      root.rotation += 8 * S(3.5 * t);
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -105 - 25 * S(11 * t);
      if (ar) ar.rotation += 105 + 25 * S(11 * t + 1);
      if (fl) fl.rotation += -45 - 20 * S(11 * t + 0.5);
      if (fr) fr.rotation += 45 + 20 * S(11 * t + 1.5);
      var ll = g('F_L_Leg_I'), lr = g('F_R_Leg_I');
      var cl = g('F_L_Calf_I'), cr = g('F_R_Calf_I');
      if (ll) ll.rotation += 18 * S(7 * t);
      if (lr) lr.rotation += -18 * S(7 * t);
      if (cl) cl.rotation += 24 * S(7 * t + 1);
      if (cr) cr.rotation += -24 * S(7 * t + 1);
      var head = g('F_Head_I');
      if (head) head.rotation += 12 * S(6 * t);
      var anch = head || root;
      topFx(fx, 'spark1', anch, -48, -42, 0.45 + 0.5 * Math.abs(S(9 * t)), '⭐');
      topFx(fx, 'spark2', anch, 44, -50, 0.45 + 0.5 * Math.abs(S(9 * t + 2)), '✨');
      topFx(fx, 'party', anch, 0, -88, 0.5 + 0.5 * Math.abs(S(5 * t)), '🎉');
    }
  };
})();
