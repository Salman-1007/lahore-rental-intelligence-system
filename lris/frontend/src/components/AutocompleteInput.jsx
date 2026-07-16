import { useEffect, useRef, useState } from "react";
import { autocompleteLocations } from "../lib/api.js";

/**
 * Free-text location input with fuzzy-matched suggestions from `/autocomplete`.
 *
 * Calls `onSelect(location)` when the person picks a suggestion, and
 * `onChangeText(text)` on every keystroke so the parent can still submit
 * a raw name if they never click a suggestion.
 */
export default function AutocompleteInput({ value, onChangeText, onSelect, placeholder }) {
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      if (value && value.trim().length > 1) {
        autocompleteLocations(value)
          .then((results) => {
            setSuggestions(results);
            setOpen(results.length > 0);
          })
          .catch(() => setSuggestions([]));
      } else {
        setSuggestions([]);
        setOpen(false);
      }
    }, 220);
    return () => clearTimeout(handle);
  }, [value]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="autocomplete" ref={containerRef}>
      <input
        className="input"
        type="text"
        value={value}
        placeholder={placeholder || "e.g. Mustafa Town"}
        onChange={(e) => onChangeText(e.target.value)}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        autoComplete="off"
      />
      {open && (
        <ul className="autocomplete-list card">
          {suggestions.map((loc) => (
            <li key={loc.id}>
              <button
                type="button"
                className="autocomplete-option"
                onClick={() => {
                  onSelect(loc);
                  setOpen(false);
                }}
              >
                <span>{loc.name}</span>
                <span className="autocomplete-level">{loc.level}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
