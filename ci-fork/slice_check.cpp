// Fork-only CI helper (not part of the upstream change).
// This file was generated with the assistance of an AI coding tool.
// Compares format_double_shortest at the base and at the change over all
// powers of two and random doubles, and times both.
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <vector>

#include "fmt_base.h"
#include "fmt_new.h"

int main() {
    std::vector<double> values;
    for (int e = -1074; e <= 1023; ++e) {
        values.push_back(std::ldexp(1.0, e));
        values.push_back(-std::ldexp(1.0, e));
    }
    std::mt19937_64 rng(10342);
    std::uniform_real_distribution<double> coord(-1e5, 1e5);
    while (values.size() < 3000000) {
        const uint64_t bits = rng();
        double v;
        std::memcpy(&v, &bits, sizeof(v));
        if (std::isfinite(v)) values.push_back(v);
        const double c = coord(rng);
        values.push_back(c);
        values.push_back(std::round(c * 1000.0) / 1000.0);
    }
    size_t diffs = 0, roundtrip_failures = 0;
    char a[64], b[64];
    for (double v : values) {
        fmt_base(a, v);
        fmt_new(b, v);
        if (std::strcmp(a, b)) {
            if (diffs++ < 5) std::printf("DIFF %.17g base=%s new=%s\n", v, a, b);
        }
        if (std::strtod(b, nullptr) != v) ++roundtrip_failures;
    }
    double ms[2];
    for (int k = 0; k < 2; ++k) {
        const auto t0 = std::chrono::steady_clock::now();
        size_t sink = 0;
        for (double v : values) {
            if (k == 0) fmt_base(a, v); else fmt_new(a, v);
            sink += a[0];
        }
        const auto t1 = std::chrono::steady_clock::now();
        ms[k] = std::chrono::duration<double, std::milli>(t1 - t0).count();
        if (sink == 42) std::printf(".");
    }
#if !defined(__APPLE__) && !defined(__EMSCRIPTEN__)
    const char* path = "to_chars";
#else
    const char* path = "search only";
#endif
    std::printf("SLICE values=%zu diffs=%zu roundtrip_failures=%zu base_ms=%.1f new_ms=%.1f path=%s\n", values.size(),
                diffs, roundtrip_failures, ms[0], ms[1], path);
    return diffs || roundtrip_failures ? 1 : 0;
}
