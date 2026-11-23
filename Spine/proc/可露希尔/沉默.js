/* 可露希尔 · 沉默（人和屏幕一起沉默：僵住盯住诡异角度里的 -8%）
 * 坐姿之上叠加：几乎静止，头微垂，手臂下垂内收，只剩极轻的呼吸。
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
  window.PROCS["沉默"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 极轻呼吸 + 头垂下去
      root.scaleY = 1 + 0.012 * S(1.6 * t);
      root.rotation += 1.5 * S(0.8 * t);
      var head = g('F_Head_I');
      if (head) head.rotation += -14 + 2.5 * S(0.8 * t);
      // 手臂垂下去（和"举手"反号），彻底泄劲
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += 20;
      if (ar) ar.rotation += -20;
      if (fl) fl.rotation += 9;
      if (fr) fr.rotation += -9;
      var anch = head || root;
      topFx(fx, 'sil1', anch, -34, -78, 0.85, '…');
      topFx(fx, 'sil2', anch, 40, -50, 0.3 + 0.2 * Math.abs(S(1.2 * t)), '💨');
    }
  };
})();
