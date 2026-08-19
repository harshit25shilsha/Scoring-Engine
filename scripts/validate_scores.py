# import asyncio
# import csv

# from app.database.postgres import PostgresSessionLocal
# from sqlalchemy import select

# from app.database.models import CandidateJobScore


# VALIDATION_DATA = [
#     {"candidate_id": 118, "human_label": "moderate", "min": 50, "max": 65},
#     {"candidate_id": 262, "human_label": "weak", "min": 35, "max": 50},
#     {"candidate_id": 198, "human_label": "weak", "min": 30, "max": 45},
#     {"candidate_id": 79, "human_label": "moderate", "min": 55, "max": 70},
#     {"candidate_id": 265, "human_label": "moderate", "min": 50, "max": 65},
#     {"candidate_id": 73, "human_label": "moderate", "min": 50, "max": 65},
#     {"candidate_id": 213, "human_label": "weak", "min": 25, "max": 40},
#     {"candidate_id": 104, "human_label": "weak", "min": 30, "max": 45},
#     {"candidate_id": 226, "human_label": "weak", "min": 25, "max": 40},
#     {"candidate_id": 223, "human_label": "weak", "min": 20, "max": 35},
#     {"candidate_id": 210, "human_label": "weak", "min": 10, "max": 25},
#     {"candidate_id": 330, "human_label": "weak", "min": 15, "max": 30},
#     {"candidate_id": 283, "human_label": "weak", "min": 5, "max": 20},
#     {"candidate_id": 311, "human_label": "weak", "min": 20, "max": 35},
#     {"candidate_id": 344, "human_label": "weak", "min": 5, "max": 20},
# ]

# JOB_ID = 6779


# async def main():
#     async with PostgresSessionLocal() as db:
#         results = []

#         for entry in VALIDATION_DATA:
#             result = await db.execute(
#                 select(CandidateJobScore).where(
#                     CandidateJobScore.job_id == JOB_ID,
#                     CandidateJobScore.candidate_id == entry["candidate_id"],
#                 )
#             )
#             row = result.scalar_one_or_none()
#             if row is None or row.overall_score is None:
#                 continue

#             system_score = row.overall_score
#             within_range = entry["min"] <= system_score <= entry["max"]

#             results.append({
#                 "candidate_id": entry["candidate_id"],
#                 "human_label": entry["human_label"],
#                 "expected_range": f"{entry['min']}-{entry['max']}",
#                 "system_score": system_score,
#                 "within_range": within_range,
#                 "gap": (
#                     0 if within_range
#                     else round(system_score - entry["max"], 1) if system_score > entry["max"]
#                     else round(entry["min"] - system_score, 1)
#                 ),
#             })

#         # Print aligned table
#         print(f"\n{'ID':<5} {'Human':<10} {'Expected':<10} {'System':<8} {'Match':<7} {'Gap'}")
#         print("-" * 55)
#         for r in results:
#             match = "YES" if r["within_range"] else "NO"
#             print(f"{r['candidate_id']:<5} {r['human_label']:<10} {r['expected_range']:<10} {r['system_score']:<8.2f} {match:<7} {r['gap']}")

#         matched = sum(1 for r in results if r["within_range"])
#         print(f"\n{matched}/{len(results)} within expected range ({round(matched/len(results)*100, 1)}%)")

#         # Ranking comparison: does system order roughly match human order?
#         print("\n--- System ranking (highest to lowest) ---")
#         for r in sorted(results, key=lambda x: x["system_score"], reverse=True):
#             print(f"  {r['candidate_id']} ({r['system_score']:.2f}) — human said: {r['human_label']}")


# asyncio.run(main())

# app/scripts/validate_scores.py

import asyncio

from app.database.postgres import PostgresSessionLocal
from sqlalchemy import select

from app.database.models import CandidateJobScore


VALIDATION_DATA = [
    # =========================
    # Job ID: 6779
    # =========================
    {"job_id": 6779, "candidate_id": 118, "human_label": "moderate", "min": 50, "max": 65},
    {"job_id": 6779, "candidate_id": 262, "human_label": "weak", "min": 35, "max": 50},
    {"job_id": 6779, "candidate_id": 198, "human_label": "weak", "min": 30, "max": 45},
    {"job_id": 6779, "candidate_id": 79, "human_label": "moderate", "min": 55, "max": 70},
    {"job_id": 6779, "candidate_id": 265, "human_label": "moderate", "min": 50, "max": 65},
    {"job_id": 6779, "candidate_id": 73, "human_label": "moderate", "min": 50, "max": 65},
    {"job_id": 6779, "candidate_id": 213, "human_label": "weak", "min": 25, "max": 40},
    {"job_id": 6779, "candidate_id": 104, "human_label": "weak", "min": 30, "max": 45},
    {"job_id": 6779, "candidate_id": 226, "human_label": "weak", "min": 25, "max": 40},
    {"job_id": 6779, "candidate_id": 223, "human_label": "weak", "min": 20, "max": 35},
    {"job_id": 6779, "candidate_id": 210, "human_label": "weak", "min": 10, "max": 25},
    {"job_id": 6779, "candidate_id": 330, "human_label": "weak", "min": 15, "max": 30},
    {"job_id": 6779, "candidate_id": 283, "human_label": "weak", "min": 5, "max": 20},
    {"job_id": 6779, "candidate_id": 311, "human_label": "weak", "min": 20, "max": 35},
    {"job_id": 6779, "candidate_id": 344, "human_label": "weak", "min": 5, "max": 20},

    # =========================
    # Job ID: 1288
    # =========================
    {"job_id": 1288, "candidate_id": 48, "human_label": "strong", "min": 75, "max": 95},
    {"job_id": 1288, "candidate_id": 204, "human_label": "strong", "min": 75, "max": 95},
    {"job_id": 1288, "candidate_id": 333, "human_label": "strong", "min": 80, "max": 100},
    {"job_id": 1288, "candidate_id": 300, "human_label": "strong", "min": 70, "max": 90},
    {"job_id": 1288, "candidate_id": 171, "human_label": "moderate", "min": 55, "max": 75},
    {"job_id": 1288, "candidate_id": 197, "human_label": "weak", "min": 15, "max": 30},
    {"job_id": 1288, "candidate_id": 270, "human_label": "weak", "min": 15, "max": 30},
    {"job_id": 1288, "candidate_id": 275, "human_label": "weak", "min": 10, "max": 25},
    {"job_id": 1288, "candidate_id": 198, "human_label": "weak", "min": 20, "max": 35},
    {"job_id": 1288, "candidate_id": 293, "human_label": "weak", "min": 15, "max": 30},
    {"job_id": 1288, "candidate_id": 322, "human_label": "weak", "min": 10, "max": 25},
    {"job_id": 1288, "candidate_id": 64, "human_label": "weak", "min": 20, "max": 40},
]


async def main():
    async with PostgresSessionLocal() as db:
        results = []

        for entry in VALIDATION_DATA:
            result = await db.execute(
                select(CandidateJobScore).where(
                    CandidateJobScore.job_id == entry["job_id"],
                    CandidateJobScore.candidate_id == entry["candidate_id"],
                )
            )

            row = result.scalar_one_or_none()

            if row is None or row.overall_score is None:
                continue

            system_score = row.overall_score
            within_range = entry["min"] <= system_score <= entry["max"]

            results.append({
                "job_id": entry["job_id"],
                "candidate_id": entry["candidate_id"],
                "human_label": entry["human_label"],
                "expected_range": f"{entry['min']}-{entry['max']}",
                "system_score": system_score,
                "within_range": within_range,
                "gap": (
                    0
                    if within_range
                    else round(system_score - entry["max"], 1)
                    if system_score > entry["max"]
                    else round(entry["min"] - system_score, 1)
                ),
            })

        # Print aligned table
        print(
            f"\n{'Job':<7} "
            f"{'ID':<6} "
            f"{'Human':<10} "
            f"{'Expected':<10} "
            f"{'System':<8} "
            f"{'Match':<7} "
            f"{'Gap'}"
        )
        print("-" * 70)

        for r in results:
            match = "YES" if r["within_range"] else "NO"

            print(
                f"{r['job_id']:<7} "
                f"{r['candidate_id']:<6} "
                f"{r['human_label']:<10} "
                f"{r['expected_range']:<10} "
                f"{r['system_score']:<8.2f} "
                f"{match:<7} "
                f"{r['gap']}"
            )

        # Overall match
        matched = sum(1 for r in results if r["within_range"])

        if results:
            percentage = round(matched / len(results) * 100, 1)
        else:
            percentage = 0

        print(
            f"\nOverall: {matched}/{len(results)} "
            f"within expected range ({percentage}%)"
        )

        # Per-job summary
        print("\n--- Per-job summary ---")

        job_ids = sorted(set(r["job_id"] for r in results))

        for job_id in job_ids:
            job_results = [
                r for r in results
                if r["job_id"] == job_id
            ]

            job_matched = sum(
                1 for r in job_results
                if r["within_range"]
            )

            job_percentage = round(
                job_matched / len(job_results) * 100,
                1
            )

            print(
                f"Job {job_id}: "
                f"{job_matched}/{len(job_results)} "
                f"within expected range ({job_percentage}%)"
            )

        # Ranking comparison per job
        for job_id in job_ids:
            print(
                f"\n--- Job {job_id}: "
                f"System ranking (highest to lowest) ---"
            )

            job_results = [
                r for r in results
                if r["job_id"] == job_id
            ]

            for r in sorted(
                job_results,
                key=lambda x: x["system_score"],
                reverse=True,
            ):
                print(
                    f"  {r['candidate_id']} "
                    f"({r['system_score']:.2f}) "
                    f"— human said: {r['human_label']}"
                )


asyncio.run(main())