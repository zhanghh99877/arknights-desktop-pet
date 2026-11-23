/* 缪缪2号 · 浇水（精灵掌心渗水：右臂伸向花盆，指尖垂落水滴）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼命名：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 * 符号（对照已验证动作）：ar 负=向外/前伸、fr 正=小臂上折；头低看盆用正角试错。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["浇水"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 右臂朝盆前伸，掌心下压轻晃（控水）；左臂自然垂摆
      var ar = g('F_Arm_R'), fr = g('F_Forearm_R');
      var al = g('F_Arm_L');
      if (ar) ar.rotation += -46 + 3 * S(2.4 * t);
      if (fr) fr.rotation += 56 + 6 * S(2.4 * t);
      if (al) al.rotation += 7 * S(1.2 * t);
      // 微微前倾低头看盆
      var head = g('F_Head');
      if (head) head.rotation += 7;
      root.rotation += 3;
      root.scaleY = 1 + 0.02 * S(2.4 * t);
      // 水滴悬在盆沿上方交错渗落（锚头部：偏移 = 壶嘴 → 盆土面的世界差）
      var anch = head || root;
      topFx(fx, 'wd1', anch, 165, 10, 0.55 + 0.45 * Math.abs(S(3.2 * t)), '💧');
      topFx(fx, 'wd2', anch, 190, -5, 0.5 + 0.45 * Math.abs(S(3.2 * t + 1.4)), '💧');
      topFx(fx, 'wd3', anch, 210, -15, 0.35 + 0.45 * Math.abs(S(4.2 * t + 0.7)), '💧');
    }
  };
})();
