import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest does not expose its lifecycle functions globally in this project, so
// Testing Library cannot register automatic cleanup on its own. Centralizing
// cleanup here prevents one component test from retaining DOM in the next.
afterEach(cleanup);
