# Generated optimization migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0006_add_performance_indexes'),
    ]

    # Use atomic = False to allow CONCURRENTLY operations
    atomic = False

    operations = [
        # Add composite indexes for common query patterns
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recipe_cuisine_difficulty ON recipes(cuisine, difficulty);",
            reverse_sql="DROP INDEX IF EXISTS idx_recipe_cuisine_difficulty;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recipe_created_user_time ON recipes(created_by_user_id, created_at);",
            reverse_sql="DROP INDEX IF EXISTS idx_recipe_created_user_time;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recipe_rating_count ON recipes(avg_rating DESC, rating_count DESC) WHERE avg_rating > 0;",
            reverse_sql="DROP INDEX IF EXISTS idx_recipe_rating_count;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recipe_prep_cook_time ON recipes(prep_time, cook_time);",
            reverse_sql="DROP INDEX IF EXISTS idx_recipe_prep_cook_time;"
        ),
        # Add GIN index for tags array queries
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recipe_tags_gin ON recipes USING gin(tags);",
            reverse_sql="DROP INDEX IF EXISTS idx_recipe_tags_gin;"
        ),
        # Add functional index for case-insensitive name searches
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recipe_name_lower ON recipes(LOWER(name));",
            reverse_sql="DROP INDEX IF EXISTS idx_recipe_name_lower;"
        ),
    ]