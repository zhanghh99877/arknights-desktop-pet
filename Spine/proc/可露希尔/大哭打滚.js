/* 可露希尔 · 大哭打滚（移植自 Desktop/animation/closure/main.js）
 * 在官方 Sleep 姿势之上叠加：纵向 2.5D 滚动（|cos| 压扁假透视）
 * + 摆手蹬脚 + 抽泣抖动 + 💦 眼泪跟随头骨。
 * 契约：注册 window.PROCS[动作名] = {base, pose(sk, t, fx)}；
 * base 为打底官方动作；fx(id, bone, dxPx, dyPx, opacity, emoji) 为
 * 运行时提供的特效辅助（骨世界坐标 + 像素偏移 → 屏幕定位）。 */
(function () {
  var S = Math.sin;

  function pose(sk, t, fx) {
    var g = function (n) { return sk.findBone(n); };
    var root = g('Bone');

    // ① 纵向滚动：|cos| 压扁，最扁保留 45% 厚度，正面回弹 100%
    var c = Math.cos(t * 3.2);
    root.scaleY = 0.45 + 0.55 * Math.abs(c);
    root.scaleX = 1 + 0.03 * S(13 * t);          // 抽泣的横向一抽一抽

    // ② 摆手：小臂相对上臂高频摆动，两只手反相
    g('F_L_Forearm_I').rotation += 40 + 35 * S(13 * t);
    g('F_R_Forearm_I').rotation += 40 - 35 * S(13 * t);
    g('F_L_Arm_II').rotation  += 15 + 20 * S(13 * t + 0.5);
    g('F_R_Arm_II').rotation  += 15 - 20 * S(13 * t + 0.5);

    // ③ 蹬脚：大腿带小腿反相踢，和摆手错开节奏
    g('F_L_Leg_I').rotation += 10 + 10 * S(8 * t + 1.2);
    g('F_R_Leg_I').rotation += 10 - 10 * S(8 * t + 1.2);
    g('F_L_Calf_I').rotation += 16 * S(8 * t + 2.1);
    g('F_R_Calf_I').rotation += -16 * S(8 * t + 2.1);

    // ④ 头跟着滚动节奏轻晃（Sleep 本身有呼吸，叠加少量即可）
    g('F_Head_I').rotation += 6 * S(13 * t + 1);

    // ⑤ 眼泪：滚到背面时藏起来
    var head = g('F_Head_I');
    if (!head) return;
    var vis = c > 0.2;
    fx('tear1', head, -30, -20, vis ? 0.5 + 0.4 * S(9 * t) : 0, '💦');
    fx('tear2', head, -55, -5,  vis ? 0.5 + 0.4 * S(9 * t + 2) : 0, '💦');
  }

  window.PROCS = window.PROCS || {};
  window.PROCS['大哭打滚'] = { base: 'Sleep', pose: pose };
})();
