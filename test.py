import unittest
import main

class PipelineTests(unittest.TestCase):
    def test_empty_goes_manual_review(self):
        self.assertEqual(main.process_one(" ")["needs_manual_review"],1)
    def test_valid_local_result(self):
        result=main.process_one("The lunch was tasty and fresh.")
        self.assertIn(result["sentiment"],["Positive","Neutral","Negative"])
        self.assertIn(result["urgency"],["Low","Medium","High"])
    def test_safety_net_raises_urgency(self):
        result=main.apply_safety_net("There was an insect in the food.",{
            "category":"Food safety / suspected contamination","sentiment":"Negative","urgency":"Low","summary":"possible insect"
        })
        self.assertEqual(result["urgency"],"High")
    def test_safety_net_does_not_lower(self):
        result=main.apply_safety_net("The meal was fine.",{
            "category":"Food quality and taste","sentiment":"Neutral","urgency":"High","summary":"fine"
        })
        self.assertEqual(result["urgency"],"High")
    def test_invalid_schema(self):
        self.assertFalse(main.is_valid({"category":"Wrong","sentiment":"Neutral","urgency":"Low","summary":"x"}))

if __name__=="__main__": unittest.main()
