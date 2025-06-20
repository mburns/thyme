# Timeline App

A beautiful timeline application built with TimelineJS3, htmx, and SQLite. Create and manage interactive timelines with ease.

## Features

- **Interactive Timeline**: Beautiful timeline visualization using TimelineJS3
- **Dynamic Content**: Real-time updates using htmx for seamless user experience
- **Event Management**: Add, view, and delete timeline events through an intuitive admin interface
- **Rich Media Support**: Include images, videos, and other media with captions and credits
- **Customization**: Set custom colors, groups, and styling for events
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **SQLite Database**: Lightweight, file-based database for easy deployment

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **Timeline**: TimelineJS3 (Knight Lab)
- **Dynamic Updates**: htmx
- **Styling**: Modern CSS with gradients and animations

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd thyme
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser** and navigate to:
   - Timeline view: `http://localhost:5000`
   - Admin interface: `http://localhost:5000/admin`

## Usage

### Viewing the Timeline
- Visit the main page to see your timeline
- Navigate through events using the timeline controls
- Click on events to see detailed information

### Managing Events
1. Go to the Admin page (`/admin`)
2. Fill out the form to add new events:
   - **Title**: Required - the main headline for the event
   - **Description**: Optional - detailed description
   - **Start Date**: Required - when the event begins
   - **End Date**: Optional - when the event ends
   - **Media URL**: Optional - link to image, video, or other media
   - **Media Caption**: Optional - caption for the media
   - **Media Credit**: Optional - attribution for the media
   - **Group**: Optional - categorize events (e.g., "Personal", "Work")
   - **Background Color**: Optional - custom background color
   - **Text Color**: Optional - custom text color

3. Click "Add Event" to save
4. Use the "Delete" button to remove events

## API Endpoints

- `GET /` - Main timeline view
- `GET /admin` - Admin interface
- `GET /api/timeline` - Timeline data in JSON format
- `GET /api/events` - List of events (for admin interface)
- `POST /api/events` - Add new event
- `DELETE /api/events/<id>` - Delete event

## Database Schema

The application uses a SQLite database with the following Event model:

```python
class Event:
    id: Integer (Primary Key)
    title: String (Required)
    description: Text
    start_date: DateTime (Required)
    end_date: DateTime
    media_url: String
    media_caption: String
    media_credit: String
    group: String
    background_color: String (Hex color)
    text_color: String (Hex color)
```

## Customization

### Timeline Configuration
Modify the TimelineJS3 configuration in `templates/index.html`:

```javascript
window.timeline = new TL.Timeline('timeline-embed', data, {
    width: '100%',
    height: '600px',
    font: 'Bevan-PotanoSans',
    scale: 'human',
    layout: 'landscape'
});
```

### Styling
Customize the appearance by editing `static/css/style.css`. The app uses modern CSS with:
- CSS Grid and Flexbox for layouts
- CSS custom properties for theming
- Smooth animations and transitions
- Responsive design patterns

## Deployment

### Local Development
The app runs in debug mode by default. For production:

1. Set environment variables:
   ```bash
   export FLASK_ENV=production
   export FLASK_DEBUG=0
   ```

2. Use a production WSGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Docker Deployment
Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [TimelineJS3](https://timeline.knightlab.com/) by Knight Lab for the timeline visualization
- [htmx](https://htmx.org/) for dynamic HTML updates
- [Flask](https://flask.palletsprojects.com/) for the web framework