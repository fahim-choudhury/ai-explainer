// Loaded by the Remotion CLI, which xv always runs from the repository root.
// Projects live in a separate workspace, so their imports of "@xv/..." and of npm packages resolve here.
import { Config } from "@remotion/cli/config";
import path from "path";

const repo = process.cwd();
Config.overrideWebpackConfig((c) => ({
  ...c,
  resolve: {
    ...c.resolve,
    alias: { ...(c.resolve?.alias ?? {}), "@xv": path.join(repo, "remotion") },
    modules: [path.join(repo, "node_modules"), "node_modules"],
  },
  resolveLoader: { ...c.resolveLoader, modules: [path.join(repo, "node_modules"), "node_modules"] },
}));
