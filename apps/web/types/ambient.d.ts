// Ambient declarations to help the editor when node_modules are not installed locally.
// These are temporary. It's best to run `npm install` in the project so real types are available.

declare module "react" {
  export type FormEvent<T = any> = any;
  export type ReactNode = any;
  export function useState<T = any>(initial?: T): [T, (v: T) => void];
  export function useEffect(fn: () => void | (() => void), deps?: any[]): void;
  export function useMemo<T>(fn: () => T, deps?: any[]): T;
  export function useCallback<T extends (...args: any[]) => any>(fn: T, deps?: any[]): T;
  const React: any;
  export default React;
  export { React };
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const jsxDEV: any;
}

declare module "lucide-react" {
  // export any used icon names as 'any'
  export const Gamepad2: any;
  export const Plus: any;
  export const Send: any;
  export const Users: any;
  export const MessageSquarePlus: any;
  export const Star: any;
  export const KeyRound: any;
  export const LogIn: any;
  export const UserPlus: any;
  export const RefreshCw: any;
  export const Shield: any;
  export const SquareChevronRight: any;
  export const Sparkles: any;
  export default any;
}

declare module "@radix-ui/react-slot" {
  export const Slot: any;
  export default Slot;
}

declare module "class-variance-authority" {
  export function cva(...args: any[]): any;
  export type VariantProps<T> = any;
}

declare module "clsx" {
  const clsx: (...args: any[]) => string;
  export { clsx };
  export default clsx;
}

declare module "tailwind-merge" {
  export function twMerge(...args: string[]): string;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
