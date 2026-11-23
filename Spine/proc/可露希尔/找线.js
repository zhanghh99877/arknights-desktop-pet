/* 可露希尔 · 找线（卡兹发展闪崩后：曲线在曲面屏边缘消失）
 * 坐姿之上叠加：双手前伸扶屏 + 头大幅左右摆找线 + 身体前倾摇摆。
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
  window.PROCS["找线"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 头大幅左右找（慢节奏），身体跟着轻微晃
      var look = S(2.4 * t);
      var head = g('F_Head_I');
      if (head) head.rotation += 34 * look;
      root.rotation += 6 * look;
      root.scaleY = 1 + 0.04 * Math.abs(S(2.4 * t));
      // 双臂前伸扶着屏幕两侧（她面向屏幕）
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -80 + 5 * look;
      if (ar) ar.rotation += 80 - 5 * look;
      if (fl) fl.rotation += -22 + 6 * S(3.1 * t);
      if (fr) fr.rotation += 22 - 6 * S(3.1 * t + 1);
      var anch = head || root;
      topFx(fx, 'find1', anch, -52, -46, 0.55 + 0.4 * Math.abs(S(4 * t)), '🔍');
      topFx(fx, 'find2', anch, 40, -64, 0.45 + 0.45 * Math.abs(S(4 * t + 2)), '❓');
    }
  };
})();
