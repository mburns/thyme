Usage Guide
==========

Viewing the Timeline
-------------------

1. Start the application (see :doc:`installation`)
2. Open your browser and navigate to http://localhost:5000
3. Use the timeline controls to navigate through events
4. Click on events to see detailed information

Managing Events
--------------

1. Go to the Admin page at http://localhost:5000/admin
2. Fill out the form to add new events:

   **Required Fields:**
   - **Title**: The main headline for the event
   - **Start Date**: When the event begins

   **Optional Fields:**
   - **Description**: Detailed description of the event
   - **End Date**: When the event ends (for events spanning multiple days)
   - **Media URL**: Link to image, video, or other media
   - **Media Caption**: Caption for the media
   - **Media Credit**: Attribution for the media
   - **Group**: Categorize events (e.g., "Personal", "Work", "Travel")
   - **Background Color**: Custom background color (hex code)
   - **Text Color**: Custom text color (hex code)

3. Click "Add Event" to save
4. Use the "Delete" button to remove events

TimelineJS3 Configuration
------------------------

The timeline is configured with the following settings:

.. code-block:: javascript

   window.timeline = new TL.Timeline('timeline-embed', data, {
       width: '100%',
       height: '600px',
       font: 'Bevan-PotanoSans',
       scale: 'human',
       layout: 'landscape'
   });

You can customize these settings by editing the configuration in ``templates/index.html``.

API Endpoints
------------

- ``GET /`` - Main timeline view
- ``GET /admin`` - Admin interface
- ``GET /api/timeline`` - Timeline data in JSON format
- ``GET /api/events`` - List of events (for admin interface)
- ``POST /api/events`` - Add new event
- ``DELETE /api/events/<id>`` - Delete event 