import GLPK from 'glpk.js';
import type { WebRouteMapWorkerRequest, WebRouteMapWorkerResponse } from './contracts.ts';
import { solveWebRouteMapLayout } from './optimizer.ts';

const solver = GLPK();

self.onmessage = async (event: MessageEvent<WebRouteMapWorkerRequest>) => {
  const { id, input } = event.data;
  try {
    const plan = await solveWebRouteMapLayout(input, await solver);
    const response: WebRouteMapWorkerResponse = { id, plan };
    self.postMessage(response);
  } catch (error) {
    const response: WebRouteMapWorkerResponse = {
      id,
      error: error instanceof Error ? error.message : 'Web map layout solver failed.',
    };
    self.postMessage(response);
  }
};
