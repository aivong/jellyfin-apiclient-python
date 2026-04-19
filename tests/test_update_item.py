"""
Tests for the update_item API method.
"""
from unittest.mock import Mock, patch, MagicMock
import pytest
from jellyfin_apiclient_python.api import API, GranularAPIMixin


class MockHTTP:
    """Mock HTTP client for testing"""
    def __init__(self, mock_client):
        self.mock_client = mock_client
    
    def request(self, request_dict):
        """Return mock response based on the request type"""
        handler = request_dict.get('handler', '')
        
        # Simulate get_item response
        if handler == 'Users/{UserId}/Items/test-item-id-123':
            return {
                'Id': 'test-item-id-123',
                'Name': 'Test Video',
                'Genres': ['Action', 'Drama'],
                'Type': 'Movie'
            }
        
        # Simulate update_item response  
        if handler == 'Users/{UserId}/Items/test-item-id-123':
            return {
                'Id': 'test-item-id-123',
                'Name': 'Test Video',
                'Genres': ['Test']
            }
        
        return {}


def test_update_item_with_genres():
    """
    Test updating an item's genre directly.
    
    This test verifies that the API can accept genres as a list of strings
    and properly merge them with existing item data.
    """
    # Create mock client with config
    mock_client = Mock()
    mock_client.config.data = {
        'auth.server': 'http://localhost:8096',
        'app.name': 'test_app',
        'app.version': '0.0.1',
        'app.device_id': 'test_device',
        'auth.user_id': 'test_user'
    }
    mock_client.request = Mock(return_value={
        'Id': 'test-item-id-123',
        'Name': 'Test Video',
        'Genres': ['Action', 'Drama'],
        'Type': 'Movie'
    })
    
    # Create API instance
    api = API(mock_client)
    
    # Test updating with genre as a list of strings
    new_genres = {"Genres": ["Test"]}
    
    # This should NOT raise an error
    with patch.object(api, 'get_item', return_value={
        'Id': 'test-item-id-123',
        'Name': 'Test Video', 
        'Genres': ['Action', 'Drama'],
        'Type': 'Movie'
    }):
        result = api.update_item('test-item-id-123', new_genres)
    
    # Verify the call was made correctly
    mock_client.request.assert_called()


def test_update_item_genres_as_list():
    """
    Test that genres can be updated when passed as a simple list.
    
    The Jellyfin API expects genres field to be a list of strings,
    not a complex object structure.
    """
    mock_client = Mock()
    mock_client.config.data = {
        'auth.server': 'http://localhost:8096',
        'app.name': 'test_app', 
        'app.version': '0.0.1',
        'app.device_id': 'test_device',
        'auth.user_id': 'test_user'
    }
    mock_client.request = Mock(return_value={
        'Id': 'test-item-id-123',
        'Name': 'Test Video',
        'Genres': ['Action', 'Drama'],
        'Type': 'Movie'
    })
    
    api = API(mock_client)
    
    # Track the request that was made
    request_payload = {}
    original_request = mock_client.request
    
    def track_request(req):
        nonlocal request_payload
        request_payload = req
        return {
            'Id': 'test-item-id-123',
            'Name': 'Test Video',
            'Genres': ['Test'],
            'Type': 'Movie'
        }
    
    mock_client.request = Mock(side_effect=track_request)
    api.client = mock_client
    
    # Patch get_item to return existing data
    with patch.object(api, 'get_item', return_value={
        'Id': 'test-item-id-123',
        'Name': 'Test Video',
        'Genres': ['Action', 'Drama'],
        'Type': 'Movie'
    }):
        result = api.update_item('test-item-id-123', {"Genres": ["Test"]})
    
    # Verify genres was passed in the json body
    assert 'json' in request_payload
    assert request_payload['json']['Genres'] == ["Test"]


def test_update_item_preserves_existing_fields():
    """
    Test that update_item preserves fields from the original item.
    
    The update_item method should fetch the full item first, then merge
    the updates, ensuring no data is lost.
    """
    mock_client = Mock()
    mock_client.config.data = {
        'auth.server': 'http://localhost:8096',
        'app.name': 'test_app',
        'app.version': '0.0.1', 
        'app.device_id': 'test_device',
        'auth.user_id': 'test_user'
    }
    
    # Track the update request
    update_request = {}
    def capture_request(req):
        nonlocal update_request
        update_request = req
        return {'Id': 'test-item-id'}
    
    mock_client.request = Mock(side_effect=capture_request)
    
    api = API(mock_client)
    
    # Simulate existing item with multiple fields
    existing_item = {
        'Id': 'test-item-id',
        'Name': 'Test Movie',
        'Genres': ['Action'],
        'Overview': 'A test movie',
        'ProviderIds': {'Tmdb': '12345'},
        'Type': 'Movie'
    }
    
    with patch.object(api, 'get_item', return_value=existing_item):
        api.update_item('test-item-id', {'Genres': ['Drama']})
    
    # The update should include all original fields plus the update
    assert 'json' in update_request
    json_body = update_request['json']
    
    # Should preserve existing fields
    assert json_body.get('Name') == 'Test Movie'
    assert json_body.get('Overview') == 'A test movie'
    assert json_body.get('ProviderIds') == {'Tmdb': '12345'}
    # And include the updated genres
    assert json_body.get('Genres') == ['Drama']


def test_update_item_uses_user_scoped_endpoint():
    """
    Test that update_item uses the user-scoped endpoint.
    
    After a Jellyfin server update, update_item started returning 500 errors.
    The fix is to use the same user-scoped endpoint as get_item:
    - /Users/{UserId}/Items/{itemId} instead of /Items/{itemId}
    
    This ensures user authentication context is passed to the server.
    """
    mock_client = Mock()
    mock_client.config.data = {
        'auth.server': 'http://localhost:8096',
        'app.name': 'test_app',
        'app.version': '0.0.1',
        'app.device_id': 'test_device',
        'auth.user_id': 'test_user_id'
    }
    
    captured_request = {}
    def capture_request(req):
        captured_request.update(req)
        return {'Id': 'test-item-id'}
    
    mock_client.request = Mock(side_effect=capture_request)
    
    api = API(mock_client)
    
    with patch.object(api, 'get_item', return_value={'Id': 'test-item-id', 'Name': 'Test'}):
        api.update_item('test-item-id', {'Genres': ['Test']})
    
    # Verify it uses the user-scoped endpoint
    handler = captured_request.get('handler', '')
    
    # Use user-scoped endpoint like get_item() pattern below
    expected_handler = 'Users/{UserId}/Items/test-item-id'
    assert handler == expected_handler, (
        f"Expected user-scoped endpoint 'Users/{{UserId}}/Items/test-item-id', "
        f"got '{handler}'."
    )