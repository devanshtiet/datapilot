import React from "react";
import {
  AbsoluteFill, Audio, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";

const BLUE = "#0052ff";
const VIOLET = "#4d7cff";
const NAVY = "#101a31";
const CLAMP = {extrapolateLeft: "clamp", extrapolateRight: "clamp"};
const fade = (frame, start, end, duration = 24) => interpolate(frame, [start, start + duration], [0, 1], {...CLAMP, easing: Easing.out(Easing.cubic)});

const Backdrop = ({frame}) => (
  <AbsoluteFill style={{background: "#f7f9fd", overflow: "hidden"}}>
    <AbsoluteFill style={{background: "radial-gradient(ellipse at 50% 45%, rgba(77,124,255,.14), transparent 48%), radial-gradient(ellipse at 50% 100%, #eaf0ff, transparent 42%)"}} />
    <div style={{position: "absolute", inset: 0, opacity: .23, backgroundImage: "radial-gradient(#b7c6e8 1px, transparent 1px)", backgroundSize: "34px 34px", maskImage: "linear-gradient(transparent, black 22%, black 82%, transparent)"}} />
    <div style={{position: "absolute", left: -220, top: 100, width: 620, height: 620, border: "1px solid #dce5f7", borderRadius: "50%", opacity: .4, transform: "scale(" + (1 + fade(frame, 0, 150, 150) * .12) + ")"}} />
    <div style={{position: "absolute", right: -210, bottom: -270, width: 720, height: 720, border: "1px solid #dce5f7", borderRadius: "50%", opacity: .38, transform: "scale(" + (1 + fade(frame, 15, 170, 155) * .1) + ")"}} />
  </AbsoluteFill>
);

const DataCards = ({frame}) => {
  const opacity = fade(frame, 142, 178, 28) * .7;
  const base = {position: "absolute", top: 390, width: 270, padding: "24px", boxSizing: "border-box", border: "1px solid #e4eaf5", borderRadius: 20, background: "rgba(255,255,255,.9)", boxShadow: "0 18px 50px rgba(31,65,130,.08)", opacity};
  return <>
    <div style={{...base, left: 230, transform: "translateY(" + interpolate(frame, [142, 210], [25, 0], CLAMP) + "px)"}}>
      <div style={{font: "600 14px Inter,sans-serif", color: "#71809a", letterSpacing: 1}}>DATA QUALITY</div>
      <div style={{font: "500 48px Inter,sans-serif", color: NAVY, marginTop: 15}}>98.2<span style={{fontSize: 18, color: "#8995a9"}}> / 100</span></div>
      <div style={{height: 5, background: "#e8eef9", borderRadius: 9, marginTop: 13}}><div style={{width: "82%", height: "100%", borderRadius: 9, background: "linear-gradient(90deg," + BLUE + "," + VIOLET + ")"}} /></div>
    </div>
    <div style={{...base, right: 230, transform: "translateY(" + interpolate(frame, [150, 218], [30, 0], CLAMP) + "px)"}}>
      <div style={{font: "600 14px Inter,sans-serif", color: "#71809a", letterSpacing: 1}}>EVIDENCE LED</div>
      <div style={{display: "flex", alignItems: "end", gap: 10, height: 80, marginTop: 12}}>
        {[38, 61, 44, 73, 54, 84, 64, 96].map((h, i) => <div key={i} style={{width: 17, height: h * .67, borderRadius: 5, background: "linear-gradient(180deg," + (i === 7 ? VIOLET : BLUE) + ",#b9ccff)", opacity: .42 + .58 * fade(frame, 157 + i * 3, 185 + i * 3, 12)}} />)}
      </div>
      <div style={{font: "13px Inter,sans-serif", color: "#71809a", marginTop: 12}}>Every metric, with its method.</div>
    </div>
  </>;
};

const Particles = ({frame}) => {
  const reveal = fade(frame, 149, 195, 35);
  const pts = Array.from({length: 36}, (_, i) => {
    const a = i * Math.PI * 2 / 36;
    const r = 140 + (i * 37 % 120) + Math.sin(frame * .035 + i * 1.7) * 7;
    return {x: 960 + Math.cos(a) * r, y: 520 + Math.sin(a) * r * .58 + interpolate(frame, [148 + i % 10 * 2, 195 + i % 10 * 2], [25, 0], CLAMP), op: reveal * (.25 + i % 5 * .1)};
  });
  return <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: "absolute", inset: 0}}>
    {pts.map((p, i) => <line key={"l" + i} x1={p.x} y1={p.y} x2={pts[(i + 1) % pts.length].x} y2={pts[(i + 1) % pts.length].y} stroke={BLUE} strokeOpacity={p.op * .24} />)}
    {pts.map((p, i) => <circle key={"p" + i} cx={p.x} cy={p.y} r={2 + i % 3} fill={i % 4 === 0 ? VIOLET : BLUE} opacity={p.op} />)}
  </svg>;
};

export const DataPilotIntro = ({title, tagline}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const icon = spring({frame: frame - 4, fps, config: {damping: 18, stiffness: 105, mass: .8}});
  const word = spring({frame: frame - 10, fps, config: {damping: 18, stiffness: 90, mass: .9}});
  const outro = fade(frame, 146, 187, 30);
  const cta = spring({frame: frame - 179, fps, config: {damping: 15, stiffness: 130, mass: .75}});
  const shineX = interpolate(frame, [155, 218], [-520, 520], CLAMP);
  return <AbsoluteFill style={{fontFamily: "Inter,Arial,sans-serif", color: NAVY, overflow: "hidden"}}>
    <Backdrop frame={frame} />
    <Audio src={staticFile("datapilot-intro.wav")} volume={interpolate(frame, [0, 8, 224, 239], [0, .82, .82, 0], CLAMP)} />
    <Particles frame={frame} /><DataCards frame={frame} />
    <div style={{position: "absolute", left: "50%", top: interpolate(frame, [0, 160], [425, 337], CLAMP), width: "100%", display: "flex", flexDirection: "column", alignItems: "center", transform: "translate(-50%,-50%) scale(" + interpolate(frame, [0, 54, 160], [.98, 1, .88], CLAMP) + ")"}}>
      <Img src={staticFile("datapilot-mark.svg")} style={{width: 126, height: 126, opacity: icon, transform: "translateY(" + interpolate(icon, [0, 1], [20, 0]) + "px) scale(" + interpolate(icon, [0, 1], [.76, 1]) + ")", filter: "drop-shadow(0 18px 34px rgba(0,82,255,.26))"}} />
      <div style={{marginTop: 27, fontSize: 90, lineHeight: 1, fontWeight: 650, letterSpacing: -5, color: NAVY, opacity: word, transform: "translateY(" + interpolate(word, [0, 1], [26, 0]) + "px)"}}>{title}<span style={{color: BLUE}}>.</span></div>
      <div style={{width: 74, height: 4, borderRadius: 8, marginTop: 27, background: "linear-gradient(90deg," + BLUE + "," + VIOLET + ")", transform: "scaleX(" + fade(frame, 30, 60, 20) + ")", opacity: interpolate(frame, [0, 152, 190], [1, 1, 0], CLAMP)}} />
      <div style={{marginTop: 30, minHeight: 46, fontSize: 31, fontWeight: 450, letterSpacing: -.6, color: "#59677f", opacity: fade(frame, 54, 91, 25) * (1 - outro), transform: "translateY(" + interpolate(frame, [54, 90], [22, 0], CLAMP) + "px)"}}>{tagline}</div>
    </div>
    <div style={{position: "absolute", top: 730, left: "50%", transform: "translate(-50%," + interpolate(cta, [0, 1], [16, 0]) + "px) scale(" + cta + ")", opacity: fade(frame, 172, 195, 15)}}>
      <div style={{position: "relative", overflow: "hidden", display: "flex", alignItems: "center", gap: 14, padding: "19px 30px", borderRadius: 999, color: "white", background: "linear-gradient(108deg," + BLUE + "," + VIOLET + ")", boxShadow: "0 16px 42px rgba(0,82,255,.25)", font: "600 21px Inter,sans-serif"}}>
        <span>Explore your data</span><span style={{fontSize: 25}}>↗</span>
        <span style={{position: "absolute", inset: 0, width: 115, transform: "translateX(" + shineX + "px) skewX(-20deg)", background: "linear-gradient(90deg,transparent,rgba(255,255,255,.34),transparent)"}} />
      </div>
    </div>
    <div style={{position: "absolute", left: "50%", bottom: 65, transform: "translateX(-50%)", opacity: fade(frame, 194, 216, 15) * .7, font: "500 15px Inter,sans-serif", letterSpacing: 3.5, color: "#78859b"}}>EVIDENCE-LED DATA ANALYSIS</div>
  </AbsoluteFill>;
};
