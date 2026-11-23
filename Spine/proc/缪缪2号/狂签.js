/* 缪缪2号 · 狂签（签文件：低头伏案，双臂高速交替签字，✍️ 闪烁）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 * 符号：al 正/ar 负 = 前伸（收红包抢夹同向）；fl 正/fr 负 = 小臂前折。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["狂签"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 伏案前倾低头
      root.rotation += 8;
      root.scaleY = 1 + 0.025 * S(9 * t);
      var head = g('F_Head');
      if (head) head.rotation += 13;
      // 双臂前伸，左右小臂高速交替抖动（笔走龙蛇）
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (al) al.rotation += 34 + 4 * S(16 * t);
      if (ar) ar.rotation += -34 - 4 * S(16 * t + Math.PI);
      if (fl) fl.rotation += 46 + 20 * S(16 * t);
      if (fr) fr.rotation += -46 - 20 * S(16 * t + Math.PI);
      // 脚尖打拍
      var cl = g('F_Calf_L'), cr = g('F_Calf_R');
      if (cl) cl.rotation += 3 * S(8 * t);
      if (cr) cr.rotation += -3 * S(8 * t);
      var anch = fr || head || root;
      topFx(fx, 'sg1', anch, 34, -34, 0.45 + 0.5 * Math.abs(S(11 * t)), '✍️');
      topFx(fx, 'sg2', anch, -40, -66, 0.35 + 0.4 * Math.abs(S(5.5 * t)), '💨');
    }
  };
})();
