/* 缪缪2号 · 叉腰（主任训话式：双手叉腰摇头，拿你不当回事）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼命名：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 * 符号：上臂 L 正/R 负=向外展开；小臂反折回腰侧。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["叉腰"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 双手叉腰：上臂外展，小臂反折收回腰侧
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (al) al.rotation += 62;
      if (ar) ar.rotation += -62;
      if (fl) fl.rotation += -92;
      if (fr) fr.rotation += 92;
      // 摇头 + 身体左右轻晃（恨铁不成钢）
      var head = g('F_Head');
      if (head) head.rotation += 10 * S(1.6 * t);
      root.rotation += 3 * S(1.6 * t);
      root.scaleY = 1 + 0.03 * Math.abs(S(3.2 * t));
      var anch = head || root;
      topFx(fx, 'hip1', anch, -52, -78, 0.5 + 0.4 * Math.abs(S(1.6 * t)), '🍃');
    }
  };
})();
