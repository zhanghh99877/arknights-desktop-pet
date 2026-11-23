/* 缪缪2号 · 收红包（红包递来：双手一夹抢过，转身藏到背后）
 * 前 0.7s 双手前伸抢，之后手臂反收背后、身体后仰两下。
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
  window.PROCS["收红包"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      var grab = t < 0.7;
      var al = g('F_Arm_L'), ar = g('F_Arm_R');
      var fl = g('F_Forearm_L'), fr = g('F_Forearm_R');
      if (grab) {
        // 双手猛地前伸一夹，身体前倾
        root.rotation += 9;
        root.scaleY = 1 + 0.05 * Math.abs(S(14 * t));
        if (al) al.rotation += 60 + 24 * S(14 * t);
        if (ar) ar.rotation += -60 - 24 * S(14 * t);
        if (fl) fl.rotation += 62;
        if (fr) fr.rotation += -62;
      } else {
        // 得手：手臂反剪背后，后仰两下，得意
        root.rotation += -9 + 3.5 * S(6 * (t - 0.7));
        root.scaleY = 1 + 0.035 * S(6 * (t - 0.7));
        if (al) al.rotation += -128;
        if (ar) ar.rotation += 128;
        if (fl) fl.rotation += -20;
        if (fr) fr.rotation += 20;
      }
      var head = g('F_Head');
      if (head) head.rotation += grab ? -6 : 8;
      var anch = head || root;
      topFx(fx, 'hong1', anch, 40, -66,
            t < 0.9 ? 0.9 : Math.max(0, 0.9 - (t - 0.9) * 2), '💰');
      if (t >= 0.7) {
        topFx(fx, 'hong2', anch, -44, -58, 0.5 + 0.4 * Math.abs(S(7 * t)), '✨');
      }
    }
  };
})();
