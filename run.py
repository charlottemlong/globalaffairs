import os
from project import create_app

port = int(os.environ.get('PORT', 2345))
app = create_app()

app.run(host='0.0.0.0', port=port)

