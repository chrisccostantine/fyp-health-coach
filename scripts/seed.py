from services.common.storage import init_db, upsert_arm
init_db()
for arm in ["coach","friendly"]:
    upsert_arm("motivation_tone", arm)
print("Seeded bandit arms.")
