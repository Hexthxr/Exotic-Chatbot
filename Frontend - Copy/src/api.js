const API = "http://localhost:5000";

export const getToken = () => localStorage.getItem("token");

export const request = async (url, method, body) => {
  const token = getToken();

  const headers = {
    "Content-Type": "application/json"
  };

  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }

  const res = await fetch(API + url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });

  return res.json();
};