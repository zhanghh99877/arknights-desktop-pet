/* 可露希尔 · 惊讶（第一个跌停日彩蛋动作）
 * 坐姿之上叠加：大幅后仰 + 高频颤抖 + 双手猛然举起 + 惊叹特效。
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 */
(function () {
  var S = Math.sin;
  window.PROCS["惊讶"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      var q = S(22 * t);
      root.scaleY = 1 + 0.10 * q;
      root.scaleX = 1 - 0.06 * q;
      root.rotation += -16 + 7 * q;
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -125 + 12 * q;
      if (ar) ar.rotation += 125 - 12 * q;
      if (fl) fl.rotation += -60 + 8 * q;
      if (fr) fr.rotation += 60 - 8 * q;
      var head = g('F_Head_I');
      if (head) head.rotation += 3600 * t / 1.14;
      var anch = head || root;
      fx('bang1', anch, -18, -86, 0.6 + 0.4 * Math.abs(S(12 * t)), '❗');
      fx('bang2', anch, 34, -62, 0.4 + 0.5 * Math.abs(S(12 * t + 1)), '💥');
    }
  };
})();
