import logo from './logo.svg';
import React from 'react';
import { useState } from 'react';
import { useEffect } from 'react';
import {io} from "socket.io-client";

import './App.css';

const socket = io("http://127.0.0.1:8080");

export default function RealTimePrediction() {
  const[text, setText] = useState("");
  const[predictions, setpredictions] = useState([]);

  socket.on("connect", ()=> console.log("connected"));
  socket.off("connect", ()=> console.log("not connected"));
  useEffect(() => {
    socket.on("prediction", (data) => {
      setpredictions((prev) => {
        if (Array.isArray(data.data)) {
          setpredictions(data.data);
        }else if (typeof(data.data) === "string"){
          setpredictions((prev) => [...prev, data.data]);
        }
        return prev;
    });
    });
    return () => socket.off("prediction");
  },[]);


  const handlechange = (e) => {
    const inputText = e.target.value;
    setText(inputText);

    if(inputText.trim()){
      socket.emit("predict", {text: inputText});
      // setpredictions([]);
    }
  };

  return (
    <div className='flex flex-col items-center p-4'>
      <input 
        type='text'
        value={text}
        onChange={handlechange}
        placeholder='type something --'
        className='border p-2 rounded-md w-96'
      />
      <div className='mt-4 p-4 border rounded-md w-96'>
        <h3 className='text-lg font-roboto'> Predictions:</h3>
        <ul>
          {predictions.map((prediction, index) =>(
            <li key={index} className='mt-2'>{prediction}</li>            
          ))}
        </ul>
      </div>
    </div>
  );
}