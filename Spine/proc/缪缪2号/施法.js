/* 缪缪2号 · 施法（召唤水分身：双臂高举画圈，脚下水纹荡开）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 * 符号：al 正=向外/前上、ar 负=向外/前上；fl/fr 反相跟随。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["施法"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 双臂高举过头，手腕交替画圈
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (al) al.rotation += 118 + 10 * S(2.6 * t);
      if (ar) ar.rotation += -118 - 10 * S(2.6 * t + Math.PI);
      if (fl) fl.rotation += 24 + 22 * S(7 * t);
      if (fr) fr.rotation += -24 - 22 * S(7 * t + Math.PI);
      // 身体随施法节奏左右摆 + 微颠
      root.rotation += 4 * S(2.6 * t);
      root.scaleY = 1 + 0.045 * Math.abs(S(5.2 * t));
      var head = g('F_Head');
      if (head) head.rotation += -6 + 3 * S(2.6 * t);
      var anch = head || root;
      topFx(fx, 'mg1', anch, 52, -102, 0.5 + 0.45 * Math.abs(S(6 * t)), '✨');
      topFx(fx, 'mg2', anch, -54, -108, 0.5 + 0.45 * Math.abs(S(6 * t + 2)), '✨');
      topFx(fx, 'mg3', anch, 0, -128, 0.55 + 0.4 * Math.abs(S(4 * t + 1)), '🌀');
    }
  };
})();
