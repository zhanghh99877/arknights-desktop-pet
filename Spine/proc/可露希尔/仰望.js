/* 可露希尔 · 仰望（跪求再带一次：仰头合十乱搓，眼里冒星星）
 * 坐姿之上叠加：仰头（正值=抬头）+ 双臂前伸小臂上折、双手在下巴前
 * 合十乱搓 + 小腿打拍；🥺 渐显、✨ 脉冲。
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
  window.PROCS["仰望"] = {
    base: "Sit",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 上身微微后仰再弹回来，呼吸起伏
      root.rotation += -4 + 1.5 * S(2.2 * t);
      root.scaleY = 1 + 0.02 * S(4.4 * t);
      // 仰头望缪缪（沉默=-14 低头 → 正值=抬头）
      var head = g('F_Head_I');
      if (head) head.rotation += 22 + 4 * S(2.2 * t);
      // 双臂前送、小臂上折，双手合在下巴前快速乱搓（乞求状）
      var al = g('F_L_Arm_II'), ar = g('F_R_Arm_II');
      var fl = g('F_L_Forearm_I'), fr = g('F_R_Forearm_I');
      if (al) al.rotation += -55 - 6 * S(5 * t);
      if (ar) ar.rotation += 55 + 6 * S(5 * t);
      if (fl) fl.rotation += -95 + 9 * S(5 * t);
      if (fr) fr.rotation += 95 - 9 * S(5 * t);
      // 腿尖点地打拍子（着急）
      var cl = g('F_L_Calf_I'), cr = g('F_R_Calf_I');
      if (cl) cl.rotation += 8 * S(4.4 * t);
      if (cr) cr.rotation += -8 * S(4.4 * t + 0.6);
      var anch = head || root;
      topFx(fx, 'beg1', anch, -52, -100, 0.55 + 0.4 * Math.abs(S(3 * t)),
            '✨');
      topFx(fx, 'beg2', anch, 46, -84, Math.min(0.95, 0.4 + t / 2.5), '🥺');
    }
  };
})();
