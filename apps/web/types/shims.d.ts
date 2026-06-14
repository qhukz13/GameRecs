// Temporary shims to quiet the editor when node_modules are not installed on the host.
// Long-term: run `npm install` locally so full types are available.

declare module "react" {
  const React: any;
  export = React;
}

declare module "react/jsx-runtime" {
  const jsx: any;
  export = jsx;
}

declare module "lucide-react" {
  const anyExport: any;
  export = anyExport;
}

declare module "@radix-ui/react-slot" {
  const anyExport: any;
  export = anyExport;
}

declare namespace JSX {
  // allow any JSX Intrinsic elements to avoid 'JSX.IntrinsicElements' missing errors
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
