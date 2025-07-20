"""
AI Integration services for MealPrepAI Django backend.
"""
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, date

logger = logging.getLogger(__name__)


@dataclass
class MealPlanRequest:
    """Data class for meal plan generation requests."""
    plan_description: str
    dietary_preferences: Optional[Dict[str, Any]] = None
    allergies: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    calorie_target: Optional[int] = None
    week_start_date: Optional[date] = None
    additional_requirements: Optional[str] = None


@dataclass
class RecipeGenerationRequest:
    """Data class for recipe generation requests."""
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: str = 'medium'
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    meal_type: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    ingredients: Optional[List[str]] = None
    additional_requirements: Optional[str] = None


class AIService:
    """Service class for AI integrations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_meal_plan(self, request: MealPlanRequest, user) -> Dict[str, Any]:
        """
        Generate a weekly meal plan using AI.
        
        For now, this returns a mock response. In production, this would
        integrate with Google Gemini or another AI service.
        """
        try:
            self.logger.info(f"Generating meal plan for user {user.id}")
            
            # Mock meal plan generation
            # In production, this would call Google Gemini API
            mock_meal_plan = {
                'name': f'AI Generated Plan - {datetime.now().strftime("%Y-%m-%d")}',
                'description': 'AI-generated healthy meal plan',
                'week_start_date': request.week_start_date or date.today(),
                'plan_description': request.plan_description,
                'analysis_text': self._generate_analysis_text(request),
                'daily_meals': self._generate_daily_meals(request)
            }
            
            self.logger.info(f"Successfully generated meal plan for user {user.id}")
            return {
                'success': True,
                'meal_plan': mock_meal_plan
            }
            
        except Exception as e:
            self.logger.error(f"Error generating meal plan for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to generate meal plan'
            }
    
    def generate_recipe_details(self, request: RecipeGenerationRequest, user) -> Dict[str, Any]:
        """
        Generate detailed recipe information using AI.
        
        For now, this returns a mock response. In production, this would
        integrate with Google Gemini or another AI service.
        """
        try:
            self.logger.info(f"Generating recipe details for user {user.id}")
            
            # Mock recipe generation
            # In production, this would call Google Gemini API
            mock_recipe = {
                'name': request.name,
                'description': request.description or f'Delicious {request.name.lower()} recipe',
                'cuisine': request.cuisine or 'International',
                'difficulty': request.difficulty,
                'prep_time': request.prep_time or 15,
                'cook_time': request.cook_time or 30,
                'ingredients': request.ingredients or self._generate_mock_ingredients(request),
                'instructions': self._generate_mock_instructions(request),
                'nutrition_info': self._generate_mock_nutrition(),
                'tags': self._generate_tags(request)
            }
            
            self.logger.info(f"Successfully generated recipe details for user {user.id}")
            return {
                'success': True,
                'recipe': mock_recipe
            }
            
        except Exception as e:
            self.logger.error(f"Error generating recipe details for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to generate recipe details'
            }
    
    def analyze_meal_plan(self, meal_plan, analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Analyze a meal plan for nutrition, variety, and balance.
        
        For now, this returns a mock response. In production, this would
        integrate with Google Gemini or another AI service.
        """
        try:
            self.logger.info(f"Analyzing meal plan {meal_plan.id}")
            
            # Mock analysis
            # In production, this would call Google Gemini API
            total_recipes = meal_plan.items.count()
            
            analysis = {
                'meal_plan_id': str(meal_plan.id),
                'analysis_type': analysis_type,
                'total_recipes': total_recipes,
                'nutrition_summary': {
                    'estimated_daily_calories': 2000 + (total_recipes * 50),
                    'protein_balance': 'Good',
                    'carb_balance': 'Moderate',
                    'fat_balance': 'Good',
                    'fiber_content': 'High',
                    'vitamin_variety': 'Excellent'
                },
                'variety_score': min(total_recipes * 10, 100),
                'balance_assessment': {
                    'meal_type_distribution': 'Well balanced across breakfast, lunch, and dinner',
                    'cuisine_variety': 'Good mix of international cuisines',
                    'cooking_methods': 'Varied preparation techniques'
                },
                'recommendations': self._generate_recommendations(meal_plan, total_recipes),
                'analysis_date': datetime.now().isoformat()
            }
            
            self.logger.info(f"Successfully analyzed meal plan {meal_plan.id}")
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing meal plan {meal_plan.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to analyze meal plan'
            }
    
    def _generate_analysis_text(self, request: MealPlanRequest) -> str:
        """Generate analysis text for meal plan."""
        parts = []
        
        if request.dietary_preferences:
            diet_type = request.dietary_preferences.get('dietType')
            if diet_type:
                parts.append(f"Designed for {diet_type} diet")
        
        if request.allergies:
            parts.append(f"Avoids allergens: {', '.join(request.allergies)}")
        
        if request.calorie_target:
            parts.append(f"Target: {request.calorie_target} calories/day")
        
        if not parts:
            parts.append("Balanced weekly meal plan with variety and nutrition")
        
        return '. '.join(parts) + '.'
    
    def _generate_daily_meals(self, request: MealPlanRequest) -> List[Dict[str, Any]]:
        """Generate mock daily meals structure."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        meal_types = ['breakfast', 'lunch', 'dinner']
        
        daily_meals = []
        for i, day in enumerate(days):
            day_meals = {
                'day': day,
                'day_of_week': i,
                'meals': {}
            }
            
            for meal_type in meal_types:
                # This would contain actual recipe recommendations from AI
                day_meals['meals'][meal_type] = {
                    'suggested_recipe_name': f'{meal_type.title()} for {day}',
                    'description': f'AI-suggested {meal_type} recipe',
                    'estimated_prep_time': 15 + (i * 2),
                    'estimated_calories': 300 + (i * 50) if meal_type == 'breakfast' else 500 + (i * 30)
                }
            
            daily_meals.append(day_meals)
        
        return daily_meals
    
    def _generate_mock_ingredients(self, request: RecipeGenerationRequest) -> List[str]:
        """Generate mock ingredients for recipe."""
        base_ingredients = [
            "2 cups all-purpose flour",
            "1 tsp salt",
            "2 tbsp olive oil",
            "1 medium onion, diced",
            "2 cloves garlic, minced"
        ]
        
        if request.meal_type == 'breakfast':
            base_ingredients.extend([
                "2 large eggs",
                "1 cup milk",
                "1 tbsp butter"
            ])
        elif request.meal_type == 'lunch':
            base_ingredients.extend([
                "1 lb protein of choice",
                "2 cups vegetables",
                "1 tbsp seasoning"
            ])
        elif request.meal_type == 'dinner':
            base_ingredients.extend([
                "1 lb main protein",
                "3 cups mixed vegetables",
                "2 tbsp herbs and spices"
            ])
        
        return base_ingredients
    
    def _generate_mock_instructions(self, request: RecipeGenerationRequest) -> str:
        """Generate mock cooking instructions."""
        return f"""
1. Prepare all ingredients by washing, chopping, and measuring as needed.

2. Heat olive oil in a large pan over medium heat. Add diced onion and cook until translucent, about 3-4 minutes.

3. Add minced garlic and cook for another minute until fragrant.

4. [Additional steps would be generated based on the specific recipe type and ingredients]

5. Season with salt and pepper to taste.

6. Serve hot and enjoy your delicious {request.name}!

Note: This is a mock recipe. In production, detailed instructions would be generated by AI based on the specific ingredients and cooking method.
        """.strip()
    
    def _generate_mock_nutrition(self) -> Dict[str, Any]:
        """Generate mock nutrition information."""
        return {
            'calories': 350,
            'protein': '25g',
            'carbohydrates': '30g',
            'fat': '15g',
            'fiber': '5g',
            'sodium': '800mg',
            'sugar': '8g',
            'servings': 4
        }
    
    def _generate_tags(self, request: RecipeGenerationRequest) -> List[str]:
        """Generate tags for recipe."""
        tags = []
        
        if request.meal_type:
            tags.append(request.meal_type)
        
        if request.difficulty:
            tags.append(request.difficulty)
        
        if request.cuisine:
            tags.append(request.cuisine.lower())
        
        if request.dietary_restrictions:
            tags.extend(request.dietary_restrictions)
        
        # Add some default tags
        if request.prep_time and request.prep_time <= 15:
            tags.append('quick')
        
        if request.cook_time and request.cook_time <= 30:
            tags.append('easy')
        
        return list(set(tags))  # Remove duplicates
    
    def _generate_recommendations(self, meal_plan, total_recipes: int) -> List[str]:
        """Generate recommendations for meal plan."""
        recommendations = []
        
        if total_recipes < 14:
            recommendations.append("Consider adding more recipe variety to cover all meals for the week")
        
        if total_recipes >= 21:
            recommendations.append("Excellent variety! You have options for all meals and snacks")
        
        recommendations.extend([
            "Include a mix of protein sources throughout the week",
            "Add colorful vegetables to increase nutrient variety",
            "Consider prep-ahead meals for busy weekdays",
            "Include healthy snacks between main meals"
        ])
        
        return recommendations


# Global AI service instance
ai_service = AIService()