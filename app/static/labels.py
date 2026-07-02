from app.static.emojis import (
    BOOK,
    BULB,
    CHECKED,
    CHEF,
    COOKING,
    DOCUMENT,
    DONE,
    ERROR,
    PLATE,
    PREVIOUS,
    SEARCH,
    SPARKLES,
)

WELCOME_MESSAGE = (
    f"שלום! {COOKING}\n"
    "אני העוזר האישי שלך למתכונים.\n"
    'פשוט ספר/י לי מה בא לך לבשל (למשל "פסטה" או "משהו עם עוף") ואני אמצא לך מתכון ממאקו.\n\n'
    "בכל שלב אפשר לשלוח /cancel כדי להתחיל מחדש."
)

HELP_MESSAGE = (
    "איך זה עובד? 🧑‍🍳\n"
    "1. ספר/י לי איזה מנה בא לך.\n"
    "2. אני אמצא 3 מתכונים ממאקו ותבחר/י אחד.\n"
    "3. נסמן יחד אילו מצרכים יש לך.\n"
    "4. אני אציע תחליפים למה שחסר.\n"
    "5. תקבל/י מתכון מותאם אישית — כמסמך מלא או צעד-אחר-צעד.\n\n"
    "/cancel - ביטול והתחלה מחדש"
)

CANCEL_MESSAGE = f"בוטל. אפשר להתחיל מחדש בכל רגע — פשוט ספר/י לי מה בא לך לבשל {PLATE}"

GENERIC_ERROR_MESSAGE = f"אופס, קרתה תקלה {ERROR} אפשר לנסות שוב?"

SEARCHING_MESSAGE = f"{SEARCH} מחפש/ת מתכונים ממאקו..."

SEARCH_RESULTS_INTRO = "מצאתי {count} מתכונים:"

SEARCH_RESULTS_PROMPT = "איזה מתכון תרצה/י?"

NO_RESULTS_MESSAGE = "לא הצלחתי למצוא מתכונים למנה הזו במאקו 😕 אפשר לנסות ניסוח אחר?"

SEARCH_FAILED_MESSAGE = f"משהו השתבש בחיפוש המתכונים {ERROR} אפשר לנסות שוב?"

AWAITING_QUERY_NUDGE = "אני עדיין מחכה/ת שתבחר/י אחת מהאפשרויות למעלה 👆"

EMPTY_QUERY_MESSAGE = "לא הצלחתי להבין איזו מנה בא לך 🤔 אפשר לנסות לתאר אותה במילים אחרות?"

LOADING_RECIPE_MESSAGE = f"{BOOK} טוען ומעבד את המתכון..."

EXTRACTION_FAILED_MESSAGE = "לא הצלחתי לטעון את עמוד המתכון 😅 אפשר לנסות מתכון אחר?"

STRUCTURING_FAILED_MESSAGE = "התקשיתי להבין את המתכון הזה 😅 אפשר לנסות מתכון אחר?"

STALE_SELECTION_MESSAGE = f"האפשרות הזו כבר לא זמינה. אפשר להתחיל חיפוש חדש {SEARCH}"

CHECKLIST_INTRO = f"סמן/י אילו מצרכים יש לך בבית {CHECKED}"

FINISHED_BUTTON = "✔ סיימתי"

PROCESSING_CHECKLIST_MESSAGE = "🔄 בודק/ת אילו מצרכים חסרים..."

SUBSTITUTION_QUESTION = "אין {ingredient} 🤔\nאפשר להשתמש ב{replacement} במקום.\n\nלהשתמש בתחליף?"

SUBSTITUTION_YES_BUTTON = "✅ כן, להשתמש בתחליף"

SUBSTITUTION_NO_BUTTON = "❌ לא, בלי זה"

SUBSTITUTION_FAILED_MESSAGE = (
    "התקשיתי להחליט מה לעשות עם המצרכים החסרים 😅 אפשר לנסות שוב מהצ'קליסט?"
)

GENERATING_FINAL_MESSAGE = f"{SPARKLES} מכין/ה עבורך את המתכון הסופי..."

FINAL_RECIPE_FAILED_MESSAGE = "לא הצלחתי להכין את המתכון הסופי 😅 אפשר לנסות שוב מהצ'קליסט?"

FINAL_RECIPE_READY_MESSAGE = SPARKLES + " המתכון מוכן: {recipe_name}!"

DELIVERY_MODE_PROMPT = "איך תרצה/י לקבל את המתכון?"

INTERACTIVE_MODE_BUTTON = f"{COOKING} בישול אינטראקטיבי"

FULL_RECIPE_MODE_BUTTON = f"{DOCUMENT} מתכון מלא"

FULL_RECIPE_INGREDIENTS_HEADER = "📝 מצרכים:"

FULL_RECIPE_INSTRUCTIONS_HEADER = f"{CHEF} הכנה:"

FULL_RECIPE_TIPS_HEADER = f"{BULB} טיפים לבישול:"

STEP_HEADER = "שלב {step_number} מתוך {total_steps}"

PREVIOUS_STEP_BUTTON = f"{PREVIOUS} הקודם"

DONE_STEP_BUTTON = f"{DONE} בוצע"

FINISH_COOKING_BUTTON = f"{DONE} סיימתי לבשל!"

COOKING_COMPLETE_MESSAGE = "🎉 כל הכבוד! סיימת לבשל את {recipe_name}. בתאבון! 😋"

WHY_BUTTON = f"{BULB} למה?"

EXPLANATION_FAILED_MESSAGE = "לא הצלחתי להסביר את השלב הזה כרגע 😅"
