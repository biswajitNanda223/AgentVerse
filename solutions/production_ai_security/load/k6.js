import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    steady: {
      executor: "constant-arrival-rate",
      rate: 40,
      timeUnit: "1s",
      duration: "3m",
      preAllocatedVUs: 40,
      maxVUs: 200,
    },
    spike: {
      executor: "ramping-arrival-rate",
      startTime: "3m",
      startRate: 10,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [{target: 150, duration: "30s"}, {target: 0, duration: "30s"}],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<750", "p(99)<1500"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const headers = {
    "content-type": "application/json",
    "x-api-key": __ENV.API_KEY || "local-development-only",
    "x-tenant-id": `load-${__VU % 10}`,
    "x-subject": `vu-${__VU}`,
    "x-scopes": "orders:read",
  };
  const response = http.post(
    `${__ENV.BASE_URL || "http://localhost:8001"}/v1/ask`,
    JSON.stringify({question: "How does human approval protect actions?"}),
    {headers},
  );
  check(response, {
    "status 200": (result) => result.status === 200,
    "no cross-tenant marker": (result) => !result.body.includes("load-secret"),
  });
}
