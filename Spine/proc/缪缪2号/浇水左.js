/* 缪缪2号 · 浇水左（左向浇花：左臂前伸控壶，水滴悬在左前方盆沿上）
 * 「浇水」的镜像版：人物朝左（flip=True）时给左侧盆栽浇水。
 * 契约：window.PROCS[动作名] = {base, pose(sk, t, fx)}。
 * 符号：al 正/fl 正 = 左臂前伸（收红包抢夹同向）；fx 偏移取负 dx。
 */
(function () {
  var S = Math.sin;
  function topFx(fx, id, bone, dx, dy, opacity, emoji) {
    fx(id, bone, dx, dy, opacity, emoji);
    var el = document.getElementById(id);
    var top = document.getElementById('overlayTop');
    if (el && top && el.parentNode !== top) top.appendChild(el);
  }
  window.PROCS["浇水左"] = {
    base: "Default",
    pose: function (sk, t, fx) {
      var g = function (n) { return sk.findBone(n); };
      var root = g('Bone');
      if (!root) return;
      // 左臂朝盆前伸，掌心下压轻晃；右臂自然垂摆
      var al = g('F_Arm_L'), fl = g('F_Forearm_L');
      var ar = g('F_Arm_R');
      if (al) al.rotation += 46 + 3 * S(2.4 * t);
      if (fl) fl.rotation += 56 + 6 * S(2.4 * t);
      if (ar) ar.rotation += -7 * S(1.2 * t);
      // 微微前倾低头看盆
      var head = g('F_Head');
      if (head) head.rotation += 7;
      root.rotation += -3;
      root.scaleY = 1 + 0.02 * S(2.4 * t);
      // 水滴悬在左前盆沿上方交错渗落（锚头部，dx 取负）
      var anch = head || root;
      topFx(fx, 'wl1', anch, -95, 10, 0.55 + 0.45 * Math.abs(S(3.2 * t)), '💧');
      topFx(fx, 'wl2', anch, -120, -5, 0.5 + 0.45 * Math.abs(S(3.2 * t + 1.4)), '💧');
      topFx(fx, 'wl3', anch, -140, -15, 0.35 + 0.45 * Math.abs(S(4.2 * t + 0.7)), '💧');
    }
  };
})();
