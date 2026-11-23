/* 缪缪2号 · 吓一跳（电话突响：猛地后仰弹起，双手甩到空中）
 * 前 0.5s 弹起后仰，之后小幅回弹抖两下站定。
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["吓一跳"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 弹起冲击：先猛后仰，指数衰减回弹
      var kick = Math.exp(-3.2 * t);
      root.rotation += -14 * kick;
      root.scaleY = 1 + 0.10 * kick * Math.abs(S(11 * t));
      root.scaleX = 1 - 0.06 * kick;
      var head = g('F_Head');
      if (head) head.rotation += -12 * kick + 2 * S(2 * t);
      // 双手甩向空中，随回弹落下
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (al) al.rotation += 95 * kick + 6 * S(3 * t) * (1 - kick);
      if (ar) ar.rotation += -95 * kick - 6 * S(3 * t) * (1 - kick);
      if (fl) fl.rotation += 30 * kick;
      if (fr) fr.rotation += -30 * kick;
      var anch = head || root;
      topFx(fx, 'sk1', anch, 0, -96, Math.max(0, 0.95 - t * 1.6), '❗');
    }
  };
})();
