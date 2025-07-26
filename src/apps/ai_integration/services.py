"""
AI Integration services for MealPrepAI Django backend.
"""
import logging
import json
import asyncio
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, date
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time

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
    """Service class for AI integrations using Google Gemini."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_gemini()
        self._rate_limit_cache_key = "ai_service_rate_limit"
        self._max_requests_per_minute = 60  # Adjust based on your API limits
    
    def _initialize_gemini(self):
        """Initialize Google Gemini AI client."""
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Configure safety settings to be less restrictive for food content
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=settings.GENAI_MODEL,
                safety_settings=self.safety_settings
            )
            
            self.logger.info("Google Gemini AI client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Gemini AI client: {str(e)}")
            raise
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        current_minute = int(time.time() // 60)
        cache_key = f"{self._rate_limit_cache_key}_{current_minute}"
        
        current_count = cache.get(cache_key, 0)
        if current_count >= self._max_requests_per_minute:
            return False
        
        cache.set(cache_key, current_count + 1, 60)  # Expire after 1 minute
        return True
    
    async def _generate_content_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Generate content with retry logic and rate limiting."""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    raise Exception("Empty response from AI model")
                    
            except Exception as e:
                self.logger.warning(f"AI generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("Failed to generate content after all retries")
    
    async def _generate_recipe_with_retry(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Generate recipe content with retry logic including JSON parsing validation."""
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                
                if not response.text:
                    raise Exception("Empty response from AI model")
                
                # Try to parse the response
                recipe_data = self._parse_recipe_details_response(response.text.strip())
                return recipe_data
                    
            except Exception as e:
                self.logger.warning(f"Recipe generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to generate valid recipe after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("Failed to generate valid recipe after all retries")
    
    async def generate_meal_plan(self, request: MealPlanRequest, user) -> Dict[str, Any]:
        """
        Generate a weekly meal plan using Google Gemini AI.
        """
        try:
            self.logger.info(f"Generating meal plan for user {user.id}")
            
            # Check cache first
            cache_key = f"meal_plan_{hash(request.plan_description)}_{user.id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Returning cached meal plan for user {user.id}")
                return cached_result
            
            # Build the prompt for meal plan generation
            prompt = self._build_meal_plan_prompt(request)
            
            # Generate content using Gemini
            response_text = await self._generate_content_with_retry(prompt)
            
            # Parse the JSON response
            meal_plan_data = self._parse_meal_plan_response(response_text)
            
            # Create the final meal plan structure
            meal_plan = {
                'name': f'AI Generated Plan - {datetime.now().strftime("%Y-%m-%d")}',
                'description': 'AI-generated healthy meal plan',
                'week_start_date': request.week_start_date or date.today(),
                'plan_description': request.plan_description,
                'analysis_text': self._generate_analysis_text(request),
                'daily_meals': meal_plan_data.get('weeklyMealPlan', [])
            }
            
            result = {
                'success': True,
                'meal_plan': meal_plan
            }
            
            # Cache the result for 1 hour
            cache.set(cache_key, result, 3600)
            
            self.logger.info(f"Successfully generated meal plan for user {user.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating meal plan for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate meal plan: {str(e)}'
            }
    
    async def generate_recipe_details(self, request: RecipeGenerationRequest, user) -> Dict[str, Any]:
        """
        Generate detailed recipe information using Google Gemini AI.
        """
        try:
            self.logger.info(f"Generating recipe details for user {user.id}")
            
            # Check cache first
            cache_key = f"recipe_details_{hash(request.name)}_{user.id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Returning cached recipe details for user {user.id}")
                return cached_result
            
            # Build the prompt for recipe generation
            prompt = self._build_recipe_details_prompt(request)
            
            # Generate content with retry and parsing validation
            recipe_data = await self._generate_recipe_with_retry(prompt)
            
            # Fetch image from Pexels API using AI-generated query
            image_url = self._fetch_pexels_image(
                recipe_name=request.name,
                cuisine=recipe_data.get('cuisine'),
                ai_query=recipe_data.get('pexels_query')
            )
                        
            recipe = {
                'name': request.name,
                'description': recipe_data.get('description', f'美味的{request.name}食谱'),
                'cuisine': recipe_data.get('cuisine', '国际'),
                'difficulty': recipe_data.get('difficulty', '中等'),
                'prep_time': int(recipe_data.get('prep_time', request.prep_time or 15)),
                'cook_time': int(recipe_data.get('cook_time', request.cook_time or 30)),
                'image_url': image_url,
                'ingredients': recipe_data.get('ingredients', []),  # List of {name, amount} objects
                'instructions': recipe_data.get('instructions', []),  # List of strings
                'nutrition_info': self._generate_mock_nutrition(),  # Keep mock for now
                'tags': recipe_data.get('tags', self._generate_tags(request))  # Use AI-generated tags or fallback
            }
                        
            result = {
                'success': True,
                'recipe': recipe
            }
            
            # Cache the result for 2 hours
            cache.set(cache_key, result, 7200)
            
            self.logger.info(f"Successfully generated recipe details for user {user.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating recipe details for user {user.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate recipe details: {str(e)}'
            }
    
    async def analyze_meal_plan(self, meal_plan, plan_description: str = '', analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Analyze a meal plan for nutrition, variety, and balance using Google Gemini AI.
        """
        try:
            self.logger.info(f"Analyzing meal plan {meal_plan.id}")
            
            # Check cache first
            cache_key = f"meal_plan_analysis_{meal_plan.id}_{hash(plan_description)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                self.logger.info(f"Returning cached analysis for meal plan {meal_plan.id}")
                return cached_result
            
            # Prepare meal plan data for analysis (using sync_to_async)
            meal_plan_data = await asyncio.to_thread(self._prepare_meal_plan_for_analysis, meal_plan)
            
            # Build the prompt for meal plan analysis
            prompt = self._build_meal_plan_analysis_prompt(plan_description, meal_plan_data)
            
            # Generate content using Gemini
            response_text = await self._generate_content_with_retry(prompt)
            
            # Parse the JSON response
            analysis_data = self._parse_analysis_response(response_text)
            
            # Get total recipes count using sync_to_async
            total_recipes = await asyncio.to_thread(lambda: meal_plan.items.count())
            
            analysis = {
                'meal_plan_id': str(meal_plan.id),
                'analysis_type': analysis_type,
                'total_recipes': total_recipes,
                'analysis_text': analysis_data.get('analysisText', ''),
                'analysis_date': datetime.now().isoformat()
            }
            
            result = {
                'success': True,
                'analysis': analysis
            }
            
            # Cache the result for 30 minutes
            cache.set(cache_key, result, 1800)
            
            self.logger.info(f"Successfully analyzed meal plan {meal_plan.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing meal plan {meal_plan.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to analyze meal plan: {str(e)}'
            }
    
    def _build_meal_plan_prompt(self, request: MealPlanRequest) -> str:
        """Build the prompt for meal plan generation using the same format as Next.js."""
        return f"""你是一位专业的膳食计划AI。你的任务是根据用户提供的计划描述生成一个7天的膳食计划。
输出必须是有效的JSON对象。所有文本内容（星期、食谱名称、配料、步骤）都应该是中文。

用户计划描述: {request.plan_description}

请生成一个JSON对象，其顶层键为 "weeklyMealPlan"。
"weeklyMealPlan" 的值应该是一个包含7个对象的数组，每周的每一天（例如，"星期一"，"星期二"，...，"星期日"）一个对象。

每个每日对象必须包含以下键：
- "day": 字符串，表示星期几。
- "breakfast": 早餐膳食对象的数组。此数组可以包含1-2个食谱。如果未计划早餐，则提供一个空数组。
- "lunch": 午餐膳食对象的数组。此数组可以包含1-2个食谱。如果未计划午餐，则提供一个空数组。
- "dinner": 晚餐膳食对象的数组。此数组可以包含1-2个食谱。如果未计划晚餐，则提供一个空数组。

"breakfast"、"lunch" 或 "dinner" 数组中的每个膳食对象必须包含以下键：
- "recipeName": 字符串，食谱的名称（例如，"牛油果吐司"，"扒鸡胸沙拉"）。
- "ingredients": 字符串数组。每个字符串应为一个详细的配料，包括具体的数量和单位（例如，"中筋面粉 1杯"，"白砂糖 1/2杯"，"2个 大鸡蛋，轻微打散"，"1个 中等大小洋葱，切碎"）。
- "instructions": 详细说明全面、分步的准备说明的字符串。包括适用的烹饪时间和温度。使用Markdown格式化步骤（例如，编号列表，**粗体**高亮关键操作）。

单个膳食对象示例：
{{
  "recipeName": "经典薄煎饼",
  "ingredients": [
    "中筋面粉 1又1/2杯",
    "泡打粉 3又1/2茶匙",
    "盐 1茶匙",
    "白砂糖 1汤匙",
    "牛奶 1又1/4杯",
    "鸡蛋 1个",
    "融化黄油 3汤匙"
  ],
  "instructions": "1. **准备面糊**: 在一个大碗里，将面粉、泡打粉、盐和糖筛在一起。\\n2. 在中心挖一个坑，倒入牛奶、鸡蛋和融化的黄油；搅拌至顺滑，不要过度搅拌。\\n3. **煎制**: 用中高火加热轻微涂油的煎锅或平底锅。当锅热时，每个薄煎饼约用1/4杯面糊倒入锅中。\\n4. **翻面**: 煎约2-3分钟，直到表面出现气泡且边缘凝固。翻面再煎1-2分钟，或至两面金黄。\\n5. **享用**: 趁热与您喜欢的配料（如枫糖浆、水果或奶油）一起享用。"
}}

确保所有字符串值都已为JSON正确转义。例如，一天的计划可能如下所示：
{{
  "day": "星期一",
  "breakfast": [
    {{ "recipeName": "燕麦粥加浆果", "ingredients": ["燕麦片 1/2杯", "水或牛奶 1杯", "混合浆果 1/2杯", "蜂蜜 1汤匙（可选）"], "instructions": "1. 将燕麦和水/牛奶在锅中混合。煮沸。\\n2. 转小火煮3-5分钟，偶尔搅拌，直至浓稠。\\n3. 如果需要，拌入浆果和蜂蜜。趁热食用。" }}
  ],
  "lunch": [
    {{ "recipeName": "烤鸡胸肉", "ingredients": ["去骨去皮鸡胸肉 1块（约150克）", "橄榄油 1汤匙", "盐 1/2茶匙", "黑胡椒 1/4茶匙", "辣椒粉 1/4茶匙"], "instructions": "1. **预热**: 将烤架或烤盘预热至中高火。\\n2. **调味**: 在鸡胸肉上涂抹橄榄油，并用盐、胡椒和辣椒粉调味。\\n3. **烤制**: 每面烤6-8分钟，或直至内部温度达到165°F（74°C）。\\n4. **静置**: 烤好后静置5分钟后再切片，以保持肉质鲜嫩。" }},
    {{ "recipeName": "简易沙拉", "ingredients": ["混合生菜叶 2杯", "黄瓜 1/4根，切片", "小番茄 4-5个，对半切", "油醋汁 1汤匙"], "instructions": "1. 在碗中混合生菜叶、黄瓜片和小番茄丁。\\n2. 淋上油醋汁，轻轻拌匀即可。" }}
  ],
  "dinner": [
    {{ "recipeName": "三文鱼配烤芦笋", "ingredients": ["三文鱼柳 1块（约150克）", "芦笋 1把，修剪", "橄榄油 1汤匙", "柠檬汁 1/2个量", "盐和胡椒 适量"], "instructions": "1. **预热烤箱**: 将烤箱预热至400°F（200°C）。\\n2. **准备蔬菜**: 将芦笋与1/2汤匙橄榄油、盐和胡椒拌匀。铺在烤盘上。\\n3. **准备三文鱼**: 在三文鱼柳上涂抹剩余的橄榄油、柠檬汁、盐和胡椒。放在同一烤盘上。\\n4. **烤制**: 烤12-15分钟，或直至三文鱼熟透，芦笋变软脆。" }}
  ]
}}
确保您的整个响应是一个以 {{ 开始并以 }} 结束的JSON对象。"""

    def _build_recipe_details_prompt(self, request: RecipeGenerationRequest) -> str:
        """Build the prompt for recipe details generation."""
        return f"""你是一位专业的烹饪助手。根据给定的食谱名称，提供完整的食谱信息。请用中文回答。

食谱名称: {request.name}

重要要求：
1. 所有配料用量必须严格按照**一人份**来计算
2. 配料名称和用量要分开，用量要精确具体
3. 烹饪步骤要详细清晰，包含具体的时间和温度
4. 所有内容必须是中文
5. 根据食谱名称自动判断菜系风格（如中式、西式、日式、韩式、意式、法式、泰式、印式等）
6. 根据食谱复杂程度自动判断难度等级（简单、中等、困难）
7. 估算合理的准备时间和烹饪时间（分钟）
8. 生成适合的标签（如素食、低脂、高蛋白、快手菜等）

字段要求：
- description: 简短的食谱描述（20-30字）
- cuisine: 菜系风格（如"中式"、"西式"、"日式"等）
- difficulty: 难度等级（"简单"、"中等"、"困难"）
- prep_time: 准备时间（分钟，整数）
- cook_time: 烹饪时间（分钟，整数）
- pexels_query: 用于Pexels图片搜索的英文关键词，要简洁且准确描述这道菜的视觉特征（如"chinese braised pork belly"、"italian pasta carbonara"、"japanese sushi rolls"等）
- ingredients: 配料列表，每个配料包含name和amount字段
- instructions: 烹饪步骤列表，每个步骤为独立字符串，不需要标出数字顺序但是应符合在数组中的顺序
- tags: 标签数组，包含相关特征标签

请严格按照以下JSON格式输出：
{{
  "description": "香嫩可口的家常鸡肉料理，营养丰富",
  "cuisine": "中式",
  "difficulty": "中等",
  "prep_time": 15,
  "cook_time": 20,
  "pexels_query": "chinese braised chicken rice bowl",
  "ingredients": [
    {{"name": "鸡胸肉", "amount": "150克"}},
    {{"name": "大米", "amount": "80克"}},
    {{"name": "生抽", "amount": "1汤匙"}},
    {{"name": "料酒", "amount": "1茶匙"}},
    {{"name": "盐", "amount": "适量"}},
    {{"name": "食用油", "amount": "1汤匙"}}
  ],
  "instructions": [
    "将鸡胸肉洗净，切成2厘米见方的小块，用料酒和少许盐腌制10分钟",
    "大米淘洗干净，放入电饭煲中，加入适量清水，按下煮饭键",
    "热锅下油，油温6成热时下入鸡肉块，大火炒制3-4分钟至表面微黄",
    "加入生抽调色调味，继续炒制2分钟至鸡肉完全熟透",
    "盛起装盘，搭配米饭一起享用"
  ],
  "tags": ["家常菜", "高蛋白", "下饭菜", "营养丰富"]
}}

请为"{request.name}"提供一个营养均衡的、一人份的完整食谱信息。确保所有字段都包含在JSON中，并且格式正确。"""

    def _build_meal_plan_analysis_prompt(self, plan_description: str, meal_plan_data: str) -> str:
        """Build the prompt for meal plan analysis."""
        return f"""你是一位专业的营养师和膳食规划顾问。
你的任务是根据用户提供的7天膳食计划数据（JSON格式）和他们的计划描述（包括饮食偏好、目标等）来进行全面的分析。
请用中文提供分析结果。分析应具有建设性并提供可操作的建议。

用户计划描述: {plan_description}

每周膳食计划数据 (JSON格式):
```json
{meal_plan_data}
```

请分析以下方面：
1.  **营养均衡性**: 评估计划是否大致包含主要营养素（蛋白质、碳水化合物、脂肪）的均衡来源。提及食物多样性（蔬菜、水果、全谷物、瘦肉蛋白等）。
2.  **与计划描述的符合程度**: 评估计划是否符合用户在 `planDescription` 中提出的偏好（例如，素食、低碳水、避免特定过敏原等）。明确指出符合和不符合的地方。
3.  **多样性和趣味性**: 评价计划中的食谱是否足够多样，以避免饮食单调。
4.  **可改进的建议**: 提供1-3条具体的、可操作的建议来改进这个膳食计划，使其更健康或更符合用户目标。建议应该清晰且易于执行。

请将您的分析结果组织成清晰、易读的段落。您可以使用Markdown格式来增强可读性，例如使用**粗体**、*斜体*或项目符号列表来突出建议。
输出应该是一个包含完整分析文本的JSON对象，键为 "analysisText"。
例如:
{{
  "analysisText": "整体来看，这个膳食计划在蛋白质摄入方面做得不错，但蔬菜种类略显单一。\\n\\n该计划很好地遵循了您"低碳水"的偏好，但需要注意补充足够的膳食纤维。\\n\\n为了进一步改善，建议：\\n* 增加不同颜色的蔬菜。\\n* 在午餐中加入一份豆类或全谷物食品。"
}}

确保输出格式为有效的JSON。"""

    def _parse_meal_plan_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the meal plan response from Gemini."""
        try:
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find JSON content between ```json and ``` markers
            json_start = response_text.find('```json')
            json_end = response_text.rfind('```')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                # Extract JSON content
                json_content = response_text[json_start + 7:json_end].strip()
            else:
                # Try to find JSON object directly
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                
                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_content = response_text[brace_start:brace_end + 1]
                else:
                    json_content = response_text
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Validate and clean the data
            if 'weeklyMealPlan' in data and isinstance(data['weeklyMealPlan'], list):
                # Ensure we have 7 days
                if len(data['weeklyMealPlan']) == 7:
                    # Validate each day
                    for day_plan in data['weeklyMealPlan']:
                        if not isinstance(day_plan, dict):
                            continue
                        
                        # Ensure required fields exist
                        for meal_type in ['breakfast', 'lunch', 'dinner']:
                            if meal_type not in day_plan:
                                day_plan[meal_type] = []
                            elif not isinstance(day_plan[meal_type], list):
                                day_plan[meal_type] = []
                            else:
                                # Filter out invalid meals
                                day_plan[meal_type] = [
                                    meal for meal in day_plan[meal_type]
                                    if (isinstance(meal, dict) and 
                                        'recipeName' in meal and 
                                        'ingredients' in meal and 
                                        'instructions' in meal and
                                        isinstance(meal['ingredients'], list))
                                ]
                    
                    return data
            
            # If validation fails, return empty structure
            return {
                'weeklyMealPlan': [
                    {
                        'day': day,
                        'breakfast': [],
                        'lunch': [],
                        'dinner': []
                    }
                    for day in ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                ]
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse meal plan JSON response: {str(e)}")
            self.logger.error(f"Response text: {response_text}")
            raise Exception("Invalid JSON response from AI model")
        except Exception as e:
            self.logger.error(f"Error parsing meal plan response: {str(e)}")
            raise

    def _parse_recipe_details_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the recipe details response from Gemini."""
        try:
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find JSON content between ```json and ``` markers
            json_start = response_text.find('```json')
            json_end = response_text.rfind('```')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                # Extract JSON content
                json_content = response_text[json_start + 7:json_end].strip()
            else:
                # Try to find JSON object directly
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                
                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_content = response_text[brace_start:brace_end + 1]
                else:
                    json_content = response_text
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Validate the data structure
            if not isinstance(data, dict):
                raise Exception("Response is not a JSON object")
            
            # Validate description field (optional, will use default if missing)
            if 'description' in data and not isinstance(data['description'], str):
                raise Exception("Invalid description field - must be a string")
            
            # Validate cuisine field (optional, will use default if missing)
            if 'cuisine' in data and not isinstance(data['cuisine'], str):
                raise Exception("Invalid cuisine field - must be a string")
            
            # Validate difficulty field (optional, will use default if missing)
            if 'difficulty' in data and not isinstance(data['difficulty'], str):
                raise Exception("Invalid difficulty field - must be a string")
            
            # Validate prep_time field (optional, will use default if missing)
            if 'prep_time' in data and not isinstance(data['prep_time'], (int, float)):
                raise Exception("Invalid prep_time field - must be a number")
            
            # Validate cook_time field (optional, will use default if missing)
            if 'cook_time' in data and not isinstance(data['cook_time'], (int, float)):
                raise Exception("Invalid cook_time field - must be a number")
            
            # Validate pexels_query field (optional, will use default if missing)
            if 'pexels_query' in data and not isinstance(data['pexels_query'], str):
                raise Exception("Invalid pexels_query field - must be a string")
            

            
            # Validate tags field (optional, will use default if missing)
            if 'tags' in data:
                if not isinstance(data['tags'], list):
                    raise Exception("Invalid tags field - must be a list")
                for i, tag in enumerate(data['tags']):
                    if not isinstance(tag, str):
                        raise Exception(f"Tag {i} is not a string")
            
            # Validate ingredients field
            if 'ingredients' not in data or not isinstance(data['ingredients'], list):
                raise Exception("Missing or invalid ingredients field")
            
            # Validate each ingredient object
            for i, ingredient in enumerate(data['ingredients']):
                if not isinstance(ingredient, dict):
                    raise Exception(f"Ingredient {i} is not an object")
                if 'name' not in ingredient or not isinstance(ingredient['name'], str):
                    raise Exception(f"Ingredient {i} missing or invalid 'name' field")
                if 'amount' not in ingredient or not isinstance(ingredient['amount'], str):
                    raise Exception(f"Ingredient {i} missing or invalid 'amount' field")
            
            # Validate instructions field
            if 'instructions' not in data or not isinstance(data['instructions'], list):
                raise Exception("Missing or invalid instructions field")
            
            # Validate each instruction
            for i, instruction in enumerate(data['instructions']):
                if not isinstance(instruction, str):
                    raise Exception(f"Instruction {i} is not a string")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse recipe details JSON response: {str(e)}")
            self.logger.error(f"Response text: {response_text}")
            raise Exception("Invalid JSON response from AI model")
        except Exception as e:
            self.logger.error(f"Error parsing recipe details response: {str(e)}")
            raise

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the meal plan analysis response from Gemini."""
        try:
            # Clean up the response text
            response_text = response_text.strip()
            
            # Find JSON content between ```json and ``` markers
            json_start = response_text.find('```json')
            json_end = response_text.rfind('```')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                # Extract JSON content
                json_content = response_text[json_start + 7:json_end].strip()
            else:
                # Try to find JSON object directly
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                
                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_content = response_text[brace_start:brace_end + 1]
                else:
                    json_content = response_text
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Validate the data
            if not isinstance(data, dict):
                raise Exception("Response is not a JSON object")
            
            if 'analysisText' not in data or not isinstance(data['analysisText'], str):
                raise Exception("Missing or invalid analysisText field")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse analysis JSON response: {str(e)}")
            self.logger.error(f"Response text: {response_text}")
            raise Exception("Invalid JSON response from AI model")
        except Exception as e:
            self.logger.error(f"Error parsing analysis response: {str(e)}")
            raise

    def _prepare_meal_plan_for_analysis(self, meal_plan) -> str:
        """Prepare meal plan data for analysis."""
        try:
            # Convert meal plan to the format expected by the analysis prompt
            daily_meals = []
            
            # Group meal plan items by day
            items_by_day = {}
            
            # Use select_related to avoid additional queries
            meal_plan_items = meal_plan.items.select_related('recipe').all()
            
            for item in meal_plan_items:
                day_name = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][item.day_of_week]
                if day_name not in items_by_day:
                    items_by_day[day_name] = {'breakfast': [], 'lunch': [], 'dinner': []}
                
                meal_data = {
                    'recipeName': item.recipe.name,
                    'ingredients': item.recipe.ingredients if isinstance(item.recipe.ingredients, list) else [],
                    'instructions': item.recipe.instructions or ''
                }
                
                items_by_day[day_name][item.meal_type].append(meal_data)
            
            # Create the weekly meal plan structure
            for day in ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]:
                daily_meals.append({
                    'day': day,
                    'breakfast': items_by_day.get(day, {}).get('breakfast', []),
                    'lunch': items_by_day.get(day, {}).get('lunch', []),
                    'dinner': items_by_day.get(day, {}).get('dinner', [])
                })
            
            return json.dumps(daily_meals, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error preparing meal plan for analysis: {str(e)}")
            return "[]"

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
    
    def _fetch_pexels_image(self, recipe_name: str, cuisine: str = None, ai_query: str = None) -> str:
        """Fetch a relevant food image from Pexels API using AI-generated query."""
        try:
            # Check if Pexels API key is configured
            pexels_api_key = getattr(settings, 'PEXELS_API_KEY', None)
            if not pexels_api_key:
                self.logger.warning("PEXELS_API_KEY not configured, using fallback image")
                return self._get_fallback_image_url()
            
            # Check cache first - include ai_query in cache key for better accuracy
            cache_key = f"pexels_image_{hash(f'{recipe_name}_{ai_query}')}"
            cached_url = cache.get(cache_key)
            if cached_url:
                return cached_url
            
            # Prepare search queries with AI-generated query as primary
            search_queries = []
            
            # Primary: Use AI-generated query if available
            if ai_query and ai_query.strip():
                search_queries.append(ai_query.strip())
            
            # Fallback queries
            search_queries.extend([
                f"{recipe_name} food",  # Secondary: specific recipe
                f"{cuisine} cuisine" if cuisine else "asian food",  # Tertiary: cuisine type
                "delicious food",  # Quaternary: generic food
                "healthy meal",  # Final: healthy food
            ])
            
            headers = {
                'Authorization': pexels_api_key
            }
            
            for query in search_queries:
                try:
                    # Make API request to Pexels
                    response = requests.get(
                        'https://api.pexels.com/v1/search',
                        params={
                            'query': query,
                            'per_page': 15,
                            'orientation': 'landscape',
                            'size': 'medium'
                        },
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        photos = data.get('photos', [])
                        
                        if photos:
                            # Get the first suitable image
                            photo = photos[0]
                            # Use medium size for better performance
                            image_url = photo['src']['medium']
                            
                            # Cache the result for 24 hours
                            cache.set(cache_key, image_url, 86400)
                            
                            query_type = "AI-generated" if query == ai_query and ai_query else "fallback"
                            self.logger.info(f"Successfully fetched Pexels image for recipe: {recipe_name} using {query_type} query: '{query}'")
                            return image_url
                    
                    elif response.status_code == 429:
                        self.logger.warning("Pexels API rate limit exceeded")
                        break  # Don't try other queries if rate limited
                    
                    elif response.status_code == 403:
                        self.logger.warning("Pexels API access forbidden - check API key")
                        break
                    
                except requests.RequestException as e:
                    self.logger.warning(f"Request failed for query '{query}': {str(e)}")
                    continue
            
            # If all searches failed, return fallback
            self.logger.warning(f"Failed to fetch Pexels image for recipe: {recipe_name}")
            return self._get_fallback_image_url()
            
        except Exception as e:
            self.logger.error(f"Error fetching Pexels image: {str(e)}")
            return self._get_fallback_image_url()
    
    def _get_fallback_image_url(self) -> str:
        """Get a fallback image URL when Pexels API fails."""
        # Use a reliable placeholder service or a default food image
        # This is a high-quality food image from Pexels that doesn't require API access
        return "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=400&h=300&fit=crop"
    
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