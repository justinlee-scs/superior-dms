import { useMemo, useState } from "react";
import { Search, Calendar, User, Tag, X, ToggleLeft, ToggleRight, Plus } from "lucide-react";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import { Calendar as CalendarComponent } from "@/app/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/app/components/ui/popover";
import { format } from "date-fns";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";

export interface FilterState {
  searchText: string;
  selectedTags: string[];
  author: string;
  dateRange: string;
  startDate?: Date;
  endDate?: Date;
  tagMatchMode?: "any" | "all"; // New: tag matching mode
}

interface SearchFiltersProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  availableTags: string[];
  availableAuthors: string[];
  onCreateTag?: (tag: string) => Promise<void> | void;
  darkMode?: boolean; // New: dark mode prop
}

export function SearchFilters({
  filters,
  onFiltersChange,
  availableTags,
  availableAuthors,
  onCreateTag,
  darkMode,
}: SearchFiltersProps) {
  const [tagSearchText, setTagSearchText] = useState("");
  const [newTagText, setNewTagText] = useState("");

  const updateFilter = (key: keyof FilterState, value: any) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const filteredAvailableTags = useMemo(() => {
    if (!tagSearchText.trim()) return availableTags;
    const q = tagSearchText.trim().toLowerCase();
    return availableTags.filter((tag) => tag.toLowerCase().includes(q));
  }, [availableTags, tagSearchText]);

  const toggleTag = (tag: string) => {
    const newTags = filters.selectedTags.includes(tag)
      ? filters.selectedTags.filter((t) => t !== tag)
      : [...filters.selectedTags, tag];
    updateFilter("selectedTags", newTags);
  };

  const clearFilters = () => {
    onFiltersChange({
      searchText: "",
      selectedTags: [],
      author: "",
      dateRange: "",
      startDate: undefined,
      endDate: undefined,
      tagMatchMode: "any", // Reset to default
    });
  };

  const hasActiveFilters =
    filters.searchText ||
    filters.selectedTags.length > 0 ||
    filters.author ||
    filters.dateRange ||
    filters.startDate ||
    filters.endDate;

  const handleCreateTag = async () => {
    const nextTag = newTagText.trim();
    if (!nextTag || !onCreateTag) return;
    await onCreateTag(nextTag);
    setNewTagText("");
  };

  return (
    <div className={`w-80 border-r p-6 space-y-6 ${darkMode ? "bg-gray-900 border-gray-700" : "bg-gray-50"}`}>
      <div className="flex items-center justify-between">
        <h2 className={`font-semibold ${darkMode ? "text-gray-100" : ""}`}>Filters</h2>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear all
          </Button>
        )}
      </div>

      {/* Search by Text */}
      <div className="space-y-2">
        <Label htmlFor="search" className={`flex items-center gap-2 ${darkMode ? "text-gray-200" : ""}`}>
          <Search className="w-4 h-4" />
          Search Documents
        </Label>
        <Input
          id="search"
          type="text"
          placeholder="Search by keyword, author, vendor..."
          value={filters.searchText}
          onChange={(e) => updateFilter("searchText", e.target.value)}
          className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500" : ""}
        />
        <p className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
          Try: "Sarah Johnson", "atlas analysis", or "phoenix acme"
        </p>
      </div>

      {/* Filter by Tags */}
      <div className={`space-y-3 rounded-xl border p-4 ${darkMode ? "border-gray-700 bg-gray-800/70" : "border-gray-200 bg-white"}`}>
        <Label className={`flex items-center gap-2 ${darkMode ? "text-gray-200" : ""}`}>
          <Tag className="w-4 h-4" />
          Tags
        </Label>
        <div className="flex flex-wrap gap-2">
          {filteredAvailableTags.map((tag) => {
            const isSelected = filters.selectedTags.includes(tag);
            return (
              <Badge
                key={tag}
                variant={isSelected ? "default" : "outline"}
                className={`cursor-pointer rounded-full px-3 py-1 text-xs ${
                  isSelected
                    ? "bg-[#020825] text-white hover:bg-[#1a2248]"
                    : darkMode
                      ? "border-gray-600 text-gray-300 hover:bg-gray-700"
                      : "border-gray-300 text-gray-700 hover:bg-gray-100"
                }`}
                onClick={() => toggleTag(tag)}
              >
                {tag}
                {isSelected && <X className="w-3 h-3 ml-1" />}
              </Badge>
            );
          })}
        </div>
        <Input
          type="text"
          placeholder="Search tags..."
          value={tagSearchText}
          onChange={(e) => setTagSearchText(e.target.value)}
          className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500" : ""}
        />
        <div className="flex gap-2">
          <Input
            type="text"
            placeholder="Create new tag..."
            value={newTagText}
            onChange={(e) => setNewTagText(e.target.value)}
            className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500" : ""}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              void handleCreateTag();
            }}
            disabled={!newTagText.trim()}
          >
            <Plus className="w-4 h-4 mr-1" />
            Create
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Label className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Match:</Label>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => updateFilter("tagMatchMode", "any")}
            className={`text-xs h-7 ${(filters.tagMatchMode || "any") === "any" ? "text-blue-500 font-medium" : darkMode ? "text-gray-400" : ""}`}
          >
            <ToggleLeft className="w-4 h-4 mr-1" />
            Any
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => updateFilter("tagMatchMode", "all")}
            className={`text-xs h-7 ${filters.tagMatchMode === "all" ? "text-blue-500 font-medium" : darkMode ? "text-gray-400" : ""}`}
          >
            <ToggleRight className="w-4 h-4 mr-1" />
            All
          </Button>
        </div>
      </div>

      {/* Filter by Author */}
      <div className="space-y-2">
        <Label htmlFor="author" className={`flex items-center gap-2 ${darkMode ? "text-gray-200" : ""}`}>
          <User className="w-4 h-4" />
          Author
        </Label>
        <Select value={filters.author || "all"} onValueChange={(value) => updateFilter("author", value === "all" ? "" : value)}>
          <SelectTrigger id="author" className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100" : ""}>
            <SelectValue placeholder="All authors" />
          </SelectTrigger>
          <SelectContent className={darkMode ? "bg-gray-800 border-gray-700" : ""}>
            <SelectItem value="all">All authors</SelectItem>
            {availableAuthors.map((author) => (
              <SelectItem key={author} value={author} className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>
                {author}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Filter by Date */}
      <div className="space-y-2">
        <Label htmlFor="date" className={`flex items-center gap-2 ${darkMode ? "text-gray-200" : ""}`}>
          <Calendar className="w-4 h-4" />
          Date Range
        </Label>
        <Select 
          value={filters.dateRange || "all"} 
          onValueChange={(value) => {
            updateFilter("dateRange", value === "all" ? "" : value);
            if (value !== "custom") {
              updateFilter("startDate", undefined);
              updateFilter("endDate", undefined);
            }
          }}
        >
          <SelectTrigger id="date" className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100" : ""}>
            <SelectValue placeholder="All time" />
          </SelectTrigger>
          <SelectContent className={darkMode ? "bg-gray-800 border-gray-700" : ""}>
            <SelectItem value="all" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>All time</SelectItem>
            <SelectItem value="today" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>Today</SelectItem>
            <SelectItem value="week" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>This week</SelectItem>
            <SelectItem value="month" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>This month</SelectItem>
            <SelectItem value="quarter" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>This quarter</SelectItem>
            <SelectItem value="year" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>This year</SelectItem>
            <SelectItem value="custom" className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}>Custom range...</SelectItem>
          </SelectContent>
        </Select>

        {/* Custom Date Range Pickers */}
        {filters.dateRange === "custom" && (
          <div className="space-y-3 pt-2">
            <div className="space-y-1">
              <Label className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-600"}`}>From Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={`w-full justify-start text-left font-normal ${darkMode ? "bg-gray-800 border-gray-700 text-gray-100 hover:bg-gray-750" : ""}`}
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    {filters.startDate ? (
                      format(filters.startDate, "PPP")
                    ) : (
                      <span className={darkMode ? "text-gray-500" : "text-gray-500"}>Pick a date</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className={`w-auto p-0 ${darkMode ? "bg-gray-800 border-gray-700" : ""}`} align="start">
                  <CalendarComponent
                    mode="single"
                    selected={filters.startDate}
                    onSelect={(date) => updateFilter("startDate", date)}
                    fromYear={1970}
                    toYear={new Date().getFullYear()}
                    captionLayout="dropdown"
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-1">
              <Label className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-600"}`}>To Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={`w-full justify-start text-left font-normal ${darkMode ? "bg-gray-800 border-gray-700 text-gray-100 hover:bg-gray-750" : ""}`}
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    {filters.endDate ? (
                      format(filters.endDate, "PPP")
                    ) : (
                      <span className={darkMode ? "text-gray-500" : "text-gray-500"}>Pick a date</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className={`w-auto p-0 ${darkMode ? "bg-gray-800 border-gray-700" : ""}`} align="start">
                  <CalendarComponent
                    mode="single"
                    selected={filters.endDate}
                    onSelect={(date) => updateFilter("endDate", date)}
                    fromYear={1970}
                    toYear={new Date().getFullYear()}
                    captionLayout="dropdown"
                    disabled={(date) =>
                      filters.startDate ? date < filters.startDate : false
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            {filters.startDate && filters.endDate && (
              <p className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
                {format(filters.startDate, "MMM d, yyyy")} →{" "}
                {format(filters.endDate, "MMM d, yyyy")}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className={`pt-4 border-t space-y-2 ${darkMode ? "border-gray-700" : ""}`}>
          <p className={`text-sm font-medium ${darkMode ? "text-gray-200" : ""}`}>Active Filters:</p>
          <div className={`space-y-1 text-sm ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
            {filters.searchText && (
              <p>• Text: "{filters.searchText}"</p>
            )}
            {filters.selectedTags.length > 0 && (
              <p>• Tags ({filters.tagMatchMode === "all" ? "ALL" : "ANY"}): {filters.selectedTags.join(", ")}</p>
            )}
            {filters.author && <p>• Author: {filters.author}</p>}
            {filters.dateRange && <p>• Date: {filters.dateRange}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
