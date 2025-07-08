<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Decentralized Energy Marketplace</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 30px;
      background-color: #f5f7fa;
    }

    h1 {
      color: #2c3e50;
      text-align: center;
    }

    form {
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
      max-width: 300px;
      gap: 10px;
    }

    input[type="text"], input[type="number"] {
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 4px;
    }

    button {
      padding: 10px;
      background-color: #2980b9;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }

    button:hover {
      background-color: #1f5f87;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      margin-top: 30px;
    }

    th, td {
      padding: 12px;
      border: 1px solid #ddd;
      text-align: center;
    }

    th {
      background-color: #34495e;
      color: white;
    }

    a {
      color: #2980b9;
      text-decoration: none;
    }

    a:hover {
      text-decoration: underline;
    }

    .center {
      display: flex;
      justify-content: center;
    }
  </style>
</head>
<body>

  <h1>Decentralized Energy Marketplace</h1>

  <div class="center">
    <form action="/offer" method="POST">
      <input type="number" name="energy" placeholder="Energy (kWh)" required>
      <input type="number" name="price" step="0.01" placeholder="Price (ETH)" required>
      <button type="submit">List Energy</button>
    </form>
  </div>

  <h2>Available Listings</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Seller</th>
        <th>Buyer</th>
        <th>Energy</th>
        <th>Price</th>
        <th>Status</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {% for t in trades %}
      <tr>
        <td>{{ t.id }}</td>
        <td>{{ t.seller }}</td>
        <td>{{ t.buyer if t.buyer != '0x0000000000000000000000000000000000000000' else 'None' }}</td>
        <td>{{ t.energy }}</td>
        <td>{{ t.price }}</td>
        <td>{{ 'Completed' if t.completed else 'Open' }}</td>
        <td>
          {% if not t.completed %}
            <a href="/buy/{{ t.id }}/{{ t.price }}">Buy</a>
          {% else %}
            -
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

</body>
</html>
