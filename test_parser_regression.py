import sys
import unittest

sys.path.insert(0, '.')

from ocr_pipeline import parse_questions_from_text


RAW_TEXT = """
PART A (10-«) 2: =!20 marks)

1. What is the objectives of machine learning.
2 Mention the various features of Machine Learning. .
6. Distinguish between Bagging and Boosting.
7, List out significant parts of biological neuron

PART B — (5 x 13 = 65 marks)
15. (a) Mention the various methods of measuring Classifier Performance with
suitable examples. (18)
Or ,
(b) List and illuminate the Guidelines for Machine Learning Experiments.
(13)
2 20070
Downloaded from EnggTree.com

PART C — (1x 15 = 15 marks)
16. (a) Discuss the supervised and unsupervised learning with example.
(b) What is KNN? Where are utilise the concept? List the importance with
example.
3 20070
Downloaded from EnggTree.com
"""


class ParserRegressionTests(unittest.TestCase):
    def test_ocr_numbering_and_page_code_noise(self):
        questions = parse_questions_from_text(RAW_TEXT)

        texts = [q["question_text"] for q in questions]

        self.assertIn("What is the objectives of machine learning", texts)
        self.assertIn("Mention the various features of Machine Learning", texts)
        self.assertIn("Distinguish between Bagging and Boosting", texts)
        self.assertIn("List out significant parts of biological neuron", texts)
        self.assertIn(
            "List and illuminate the Guidelines for Machine Learning Experiments",
            texts,
        )
        self.assertIn(
            "Discuss the supervised and unsupervised learning with example",
            texts,
        )
        self.assertIn(
            "What is KNN? Where are utilise the concept? List the importance with example",
            texts,
        )

        self.assertNotIn("2", texts)
        self.assertFalse(any(text.endswith(" 3") for text in texts))

        guideline_question = next(
            q for q in questions
            if q["question_text"] == "List and illuminate the Guidelines for Machine Learning Experiments"
        )
        self.assertEqual(guideline_question["marks"], 13.0)


if __name__ == "__main__":
    unittest.main()
