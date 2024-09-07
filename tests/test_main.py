import pytest
from main import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome' in response.data  # Check for content in the page


def test_generate_itinerary(client, monkeypatch):
    # Mock the OpenAI response for the itinerary
    def mock_generate_itinerary_prompt(*args, **kwargs):
        return "Itinerary for Rome, Florence, Venice."

    monkeypatch.setattr('main.generate_itinerary',
                        mock_generate_itinerary_prompt)

    response = client.post('/generate-itinerary',
                           data={
                               'country': 'Italy',
                               'duration': '7',
                               'activities': ['sightseeing', 'culture']
                           })

    assert response.status_code == 200
    assert b'Rome' in response.data  # Check if "Rome" is in the response HTML
