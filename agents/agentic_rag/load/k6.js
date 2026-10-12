import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    interactive: {
      executor: "ramping-arrival-rate",
      startRate: 1,
      timeUnit: "1s",
      preAllocatedVUs: 20,
      maxVUs: 100,
      stages: [
        { target: 20, duration: "1m" },
        { target: 50, duration: "3m" },
        { target: 0, duration: "30s" },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
  },
};

export default function () {
  const response = http.post(
    `${__ENV.BASE_URL || "http://localhost:8000"}/v1/ask`,
    JSON.stringify({ question: "What is semantic retrieval?", mode: "semantic" }),
    {
      headers: {
        "content-type": "application/json",
        "x-api-key": __ENV.API_KEY || "local-only",
        "x-tenant-id": "load-test",
      },
    },
  );
  check(response, { "status 200": (result) => result.status === 200 });
}
