/* 可露希尔 · 暴怒（多索雷斯啤酒阴跌到跌停：从懵转怒，拍桌砸拳）
 * 坐姿之上叠加：双拳轮流往下砸 + 身体砸一下弹一下 + 愤怒摇头跺脚。
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
  window.PROCS["暴怒"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 砸一下弹一下（5Hz 弹跳），身体随出拳左右拧
      root.scaleY = 1 + 0.11 * Math.abs(S(5 * t));
      root.scaleX = 1 - 0.05 * Math.abs(S(5 * t));
      root.rotation += 9 * S(10 * t + 0.4);
      // 双拳轮流高举→猛砸（反相）
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -78 + 68 * S(10 * t);
      if (ar) ar.rotation += -78 + 68 * S(10 * t + Math.PI);
      if (fl) fl.rotation += 34 * S(20 * t);
      if (fr) fr.rotation += -34 * S(20 * t);
      // 愤怒摇头 + 跺脚
      var head = g('F_Head_I');
      if (head) head.rotation += 16 * S(10 * t + 0.8);
      var cl = g('F_L_Calf_I'), cr = g('F_R_Calf_I');
      if (cl) cl.rotation += -18 * Math.abs(S(10 * t + 1.2));
      if (cr) cr.rotation += 18 * Math.abs(S(10 * t + 1.7));
      var anch = head || root;
      topFx(fx, 'rage1', anch, -48, -66, 0.5 + 0.5 * Math.abs(S(10 * t)), '💢');
      topFx(fx, 'rage2', anch, 44, -84, 0.4 + 0.5 * Math.abs(S(10 * t + 1.5)), '💥');
    }
  };
})();
