import unittest

from services.llm_service import LLMService


class RouteMapParsingTest(unittest.TestCase):
    def test_extract_route_info_from_structured_response(self):
        service = LLMService.__new__(LLMService)
        response = '''{
            "answer": "从南门出发，前往灵山大佛最顺畅。",
            "route_intent": true,
            "route_data": {
                "origin": "南门",
                "destination": "灵山大佛",
                "waypoints": ["佛足坛", "九龙灌浴"],
                "mode": "walk",
                "summary": "适合步行游览"
            }
        }'''

        result = service.extract_route_info("怎么去灵山大佛", response)

        self.assertTrue(result["route_intent"])
        self.assertEqual(result["route_data"]["destination"], "灵山大佛")
        self.assertEqual(result["route_data"]["origin"], "南门")


if __name__ == '__main__':
    unittest.main()
