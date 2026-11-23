/* 缪缪2号 · 装傻（被套消息时：歪头摊手吹口哨，一脸无辜）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼命名：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["装傻"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 歪头 + 轻晃，身体一耸一耸
      var head = g('F_Head');
      if (head) head.rotation += 18 * S(1.3 * t) + 7;
      root.scaleY = 1 + 0.04 * Math.abs(S(2.6 * t));
      root.rotation += 2.5 * S(1.3 * t);
      // 双臂摊开掌心朝上，再收回来（摊手吹口哨）
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      var open = 36 * Math.abs(S(1.3 * t));
      if (al) al.rotation += 20 + open;
      if (ar) ar.rotation += -20 - open;
      if (fl) fl.rotation += 12 + 8 * S(2.6 * t);
      if (fr) fr.rotation += -12 - 8 * S(2.6 * t + 1);
      var anch = head || root;
      topFx(fx, 'inn1', anch, 44, -62, 0.5 + 0.4 * Math.abs(S(2.2 * t)), '🎵');
      topFx(fx, 'inn2', anch, -46, -70, 0.45 + 0.4 * Math.abs(S(2.2 * t + 1.5)), '😇');
    }
  };
})();
