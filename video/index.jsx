import React from "react";
import {Composition, registerRoot} from "remotion";
import {DataPilotIntro} from "./src/DataPilotIntro.jsx";

const Root = () => <Composition
  id="DataPilotIntro"
  component={DataPilotIntro}
  durationInFrames={240}
  fps={30}
  width={1920}
  height={1080}
  defaultProps={{title: "DataPilot", tagline: "Know what your data is saying."}}
/>;

registerRoot(Root);
