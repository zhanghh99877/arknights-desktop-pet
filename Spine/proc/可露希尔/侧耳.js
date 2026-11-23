/* 可露希尔 · 侧耳（凑过去听悄悄话：手拢在耳后，头歪向对方）
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
  window.PROCS["侧耳"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 前倾 + 头使劲歪向说话的人，一动不动生怕漏一个字
      root.rotation += 8;
      root.scaleY = 1 + 0.015 * S(1.8 * t);
      var head = g('F_Head_I');
      if (head) head.rotation += 24 + 3 * S(1.8 * t);
      // 一手拢在耳后（举臂），另一只手垂着
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (ar) ar.rotation += -98 + 4 * S(2.4 * t);
      if (fr) fr.rotation += -118 + 6 * S(2.4 * t);
      if (al) al.rotation += 14;
      var anch = head || root;
      topFx(fx, 'ear1', anch, -40, -72, 0.8, '👂');
      topFx(fx, 'ear2', anch, 42, -46, 0.4 + 0.3 * Math.abs(S(1.2 * t)), '❓');
    }
  };
})();
