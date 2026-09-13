import { Component } from "react";
import { LottieSvg } from "lottie-react";

// lottie-react v3 exports the component as a named export and takes animation
// data via `src`. `LottieSvg` renders SVG-only, keeping the bundle lean. Any
// parse/render failure must never take down the page — fall back to a simple
// CSS pulse instead.
export default class SafeLottie extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <span className="coin-fallback" aria-hidden="true" />;
    }
    return (
      <LottieSvg
        src={this.props.src}
        loop={this.props.loop ?? true}
        autoplay={this.props.autoplay ?? true}
        style={this.props.style}
        className={this.props.className}
      />
    );
  }
}