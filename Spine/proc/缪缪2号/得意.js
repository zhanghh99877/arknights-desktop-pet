/* 缪缪2号 · 得意（胸有成竹：歪头，左手握拳举起，右手举到头侧挥✌️）
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 缪缪2号骨骼命名：F_Head / F_Arm_L,R / F_Forearm_L,R / F_Leg_L,R / F_Calf_L,R。
 * 符号（对照已验证动作）：ar 负=向外展开（装傻摊手）、fr 正=向前上折（耳语 92）。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["得意"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 歪头 + 身体左右轻摆，脚下打拍一颠一颠
      var head = g('F_Head');
      if (head) head.rotation += 12 + 6 * S(1.6 * t);
      root.rotation += 2.5 * S(0.8 * t);
      root.scaleY = 1 + 0.035 * Math.abs(S(3.2 * t));
      // 左臂前送握拳举肩（「就说吧！」）；右臂外展、小臂上折到手侧挥
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (al) al.rotation += 34;
      if (fl) fl.rotation += 62;
      if (ar) ar.rotation += -60 + 6 * S(3.2 * t);
      if (fr) fr.rotation += 100 + 14 * S(3.2 * t);
      // 小腿交替点地
      var cl = g('F_Calf_L'), cr = g('F_Calf_R');
      if (cl) cl.rotation += 4 * S(3.2 * t);
      if (cr) cr.rotation += -4 * S(3.2 * t + 1);
      var anch = head || root;
      topFx(fx, 'sm1', anch, 56, -86, 0.9, '😏');
      topFx(fx, 'sm2', anch, -58, -104, 0.4 + 0.45 * Math.abs(S(2.4 * t)),
            '✌️');
    }
  };
})();
