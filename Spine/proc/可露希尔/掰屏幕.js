/* 可露希尔 · 掰屏幕（把曲面屏掰过来找那根消失的线）
 * 坐姿之上叠加：双臂高举抓住屏幕发力回拽 + 身体后仰使劲 + 高频颤抖。
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
  window.PROCS["掰屏幕"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 后仰发力 + 高频较劲颤抖
      root.rotation += -12 + 6 * S(9 * t) + 2.5 * S(27 * t);
      root.scaleY = 1 + 0.06 * Math.abs(S(9 * t));
      root.scaleX = 1 - 0.04 * Math.abs(S(9 * t));
      // 双臂高举抓屏，一下一下往回拽
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -136 + 40 * S(9 * t);
      if (ar) ar.rotation += 136 - 40 * S(9 * t + 0.7);
      if (fl) fl.rotation += -46 + 22 * S(9 * t + 0.4);
      if (fr) fr.rotation += 46 - 22 * S(9 * t + 1.1);
      // 双腿蹬地较劲
      var ll = g('F_L_Leg_I'), lr = g('F_R_Leg_I');
      var cl = g('F_L_Calf_I'), cr = g('F_R_Calf_I');
      if (ll) ll.rotation += 10 * S(9 * t + 2);
      if (lr) lr.rotation += -10 * S(9 * t + 2);
      if (cl) cl.rotation += 16 * S(9 * t + 2.6);
      if (cr) cr.rotation += -16 * S(9 * t + 2.6);
      var head = g('F_Head_I');
      if (head) head.rotation += 8 * S(9 * t + 1.5);
      var anch = head || root;
      topFx(fx, 'bend1', anch, -46, -70, 0.5 + 0.5 * Math.abs(S(9 * t)), '💢');
      topFx(fx, 'bend2', anch, 42, -58, 0.45 + 0.5 * Math.abs(S(9 * t + 1.8)), '💦');
    }
  };
})();
