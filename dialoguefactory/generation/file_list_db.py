#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the FileListDb class that stores sentences and flushes them in a file when needed.
"""
import copy
import os
from file_read_backwards import FileReadBackwards


class ListDb:
    """
        Extends the functionality of a list by:

            - flushing the elements if the list reaches a certain number of elements.
            - copying the elements before adding them to the list (The elements should have a mycopy method)

        This class is useful for storing the context sentences so that RAM does not get full as the simulation runs.

        Attributes
        ----------
        elements : list
            The elements of the list. The elements can be of any type.
        num_flush : int
            The number of elements to be removed when the flush function is called.
        num_elements : int
            The number of elements that the list of elements has.

    """
    def __init__(self, elements=None, num_flush=None):
        self.elements = list() if elements is None else elements
        self.num_flush = num_flush
        self.num_elements = len(self.elements)

    def __getitem__(self, idx):
        """ Queries an element from the list by index or multiple elements using a slice start_idx:end_idx:step.
            This function is used so that this class will behave like a list. For example,
            the following operations are possible:
            instance = FileListDb([sent1, sent2, sent3, sent4])
            > instance[0:2]
            [sent1, sent2]
            > instance[1]
            [sent2]
        """

        if isinstance(idx, int):
            return self.elements[idx]
        elif isinstance(idx, slice):
            elements = []
            border = self.num_elements - len(self.elements)
            start_at, stop_at, step = self.separate_slice(idx)
            # there are 3 cases. two when inside the file, one that goes both ways and one only outside the file
            if stop_at > start_at >= border:
                elements += self.elements[start_at-border:stop_at-border:step]

            return elements

    def __delitem__(self, idx):
        """ Deletes an element from the list by index or multiple elements using a range start_idx:end_idx:step.
            This function is used so that this class will behave like a list. For example,
            the following operations are possible:
            instance = FileListDb([sent1, sent2, sent3, sent4])
            > del instance[0:2]
            [sent3, sent4]
            > del instance[0]
            [sent2, sent3, sent4]
        """
        if isinstance(idx, int):
            del self.elements[idx]
            self.num_elements -= 1
        elif isinstance(idx, slice):
            border = self.num_elements - len(self.elements)
            start_at, stop_at, step = self.separate_slice(idx)

            # there are 3 cases. two when inside the file, one that goes both ways and one only outside the file
            if stop_at > start_at >= border:
                num_removed_list = len(self.elements[start_at-border:stop_at-border:step])
                del self.elements[start_at-border:stop_at-border:step]
                self.num_elements -= num_removed_list

    def __len__(self):
        """ Returns the length of the list. This method is used so that the following is possible:
            instance = FileListDb([sent1, sent2, sent3, sent4])
            > len(instance)
            4
        """
        return self.num_elements

    def get(self, last_num_elements):
        """ Gets the last number of elements from the list.
        """
        elements = []
        if len(self.elements) >= last_num_elements:
            if last_num_elements > 0:
                elements = self.elements[-last_num_elements:]

        return elements

    def flush(self):
        """ Removes the first self.num_flush elements from the list.
        """
        if self.num_flush is None:
            num_flush = self.num_elements
        else:
            num_flush = self.num_flush
        del self.elements[0:num_flush]

    def add(self, new_elements, serialize=False):
        """ Adds the elements to the list. If the parameter serialize is set to True,
            it copies them using the mycopy method before adding them.
            Copying is useful when you would like to preserve the Entity state since the entities change over time.
        """
        memo = dict()
        for elem in new_elements:
            if serialize and callable(getattr(elem, "mycopy", None)):
                copied_elem = elem.mycopy(memo)
            else:
                copied_elem = elem
            self.elements.append(copied_elem)
        self.num_elements += len(new_elements)
        serialized_elements = self.elements[len(self.elements) - len(new_elements):]
        return serialized_elements

    def separate_slice(self, slice_):
        """ Separates a slice start:step:stop into start, step, stop."""
        if slice_.stop is None:
            stop_at = self.num_elements
        else:
            stop_at = slice_.stop
        if slice_.start is None:
            start_at = 0
        else:
            start_at = slice_.start
        if slice_.step is None:
            step = 1
        else:
            step = slice_.step

        if start_at < 0:
            start_at = self.num_elements + start_at
        if stop_at < 0:
            stop_at = self.num_elements + stop_at

        return start_at, stop_at, step

    def save_state(self):
        """ Returns a copy of the configuration of the list """
        return copy.copy(self.elements), self.num_elements

    def recover_state(self, state):
        """ Recovers the state of the list without losing the original reference."""
        del self.elements[:]
        self.elements.extend(state[0])
        self.num_elements = state[1]


class StringListDb(ListDb):
    """
      Extends the functionality of a ListDb by:

            - storing the elements in a file (The elements should have the to_string method if they are not strings).
            - flushing the elements in a file if the list reaches a certain number of elements.
            - fetching and deleting the elements in the file.

      Attributes
      ----------
      file_name : str
            The file name where the elements will be saved when the flush function is called.
    """

    def __init__(self, file_name, elements=None, num_flush=None):
        super().__init__(elements, num_flush)
        self.file_name = file_name

        with open(self.file_name, 'a'):
            pass

    def __getitem__(self, idx):
        """ Queries an element from the list by index or multiple elements using a range start_idx:end_idx:step.
            If the range goes beyond the list boundaries, the list elements can be fetched from the file.
        """

        if isinstance(idx, int):
            return self.elements[idx]
        elif isinstance(idx, slice):
            elements = []
            border = self.num_elements - len(self.elements)
            start_at, stop_at, step = self.separate_slice(idx)
            # there are 3 cases. two when inside the file, one that goes both ways and one only outside the file
            if stop_at > start_at >= border:
                elements += self.elements[start_at-border:stop_at-border:step]
            if border >= stop_at > start_at:
                elements += self.load_slice_from_file(start_at, stop_at, step)
            if start_at <= border <= stop_at:
                elements += self.load_slice_from_file(start_at, border, step)
                elements += self.elements[0:stop_at-border:step]
            return elements

    def __delitem__(self, idx):
        """ Deletes an element from the list by index or multiple elements using a range start_idx:end_idx:step.
            If the range goes outside the list boundaries, the list elements that are stored in a file are
            deleted.
        """
        if isinstance(idx, int):
            del self.elements[idx]
        elif isinstance(idx, slice):
            border = self.num_elements - len(self.elements)
            start_at, stop_at, step = self.separate_slice(idx)

            # there are 3 cases. two when inside the file, one that goes both ways and one only outside the file
            if stop_at > start_at >= border:
                num_removed_list = len(self.elements[start_at-border:stop_at-border:step])
                del self.elements[start_at-border:stop_at-border:step]
                self.num_elements -= num_removed_list
            if border >= stop_at > start_at:
                num_removed = self.remove_slice_from_file(start_at, stop_at, step)
                self.num_elements -= num_removed
            if start_at <= border <= stop_at:
                num_removed_file = self.remove_slice_from_file(start_at, border, step)
                num_removed_list = len(self.elements[0:stop_at - border:step])
                del self.elements[0:stop_at - border:step]
                self.num_elements = self.num_elements - (num_removed_file + num_removed_list)

    def get(self, last_num_elements):
        """ Gets the last number of elements from the list. This function
            is faster compared to __getitem__ when fetching the last_num_elements because it fetches
            the elements from the end of the file.
        """

        if len(self.elements) < last_num_elements:
            rest = self.reverse_load_from_file(last_num_elements-len(self.elements))
            elements = rest + self.elements
        else:
            if last_num_elements == 0:
                elements = []
            else:
                elements = self.elements[-last_num_elements:]

        return elements

    def flush(self):
        """ Removes the first self.num_flush elements from the list
            and saves them to a file if the filename is available.
        """
        if self.num_flush is None:
            num_flush = self.num_elements
        else:
            num_flush = self.num_flush
        self.save_to_file(num_flush)
        del self.elements[0:num_flush]

    def save_to_file(self, num_elem):
        """ Saves the last <num_elem> elements to a file. """
        if self.file_name is not None:
            with open(self.file_name, "a") as outfile:
                for sent in self.elements[0:num_elem]:
                    if isinstance(sent, str):
                        outfile.write(sent + "\n")

    def reverse_load_from_file(self, num_elem):
        """ Loads the last num_elem from file by iterating through the file in reversed order. """
        elements = []
        if self.file_name is not None:
            with FileReadBackwards(self.file_name, encoding="utf-8") as frb:
                line_counter = 0
                while True:
                    if line_counter >= num_elem:
                        break
                    line = frb.readline().strip()
                    elements.append(line)
                    line_counter += 1
        return list(reversed(elements))

    def load_slice_from_file(self, start_index, end_index, step):
        """ Loads a slice of the list of elements stored in the file self.file_name.
            The elements are taken from start_index to end_index. If the step is available,
            each step-th element is taken.
        """
        sliced_lines = []
        with open(self.file_name, 'r') as file:
            # Skip lines until start_index
            for _ in range(start_index):
                next(file, None)

            # Read lines until end_index
            for line_number in range(start_index, end_index):

                line = file.readline().strip()
                if not line:
                    break
                if (line_number - start_index) % step == 0:
                    sliced_lines.append(line)

        return sliced_lines

    def remove_slice_from_file(self, start_index, end_index, step):
        """ Removes a slice of the list of elements stored in the file self.file_name.
            The elements removed are from start_index to end_index, skipping each <step> element.
        """
        temp_file_path = 'temp_file.txt'
        num_removed = 0
        with open(self.file_name, 'r') as original_file, open(temp_file_path, 'w') as temp_file:
            # Copy lines from the original file to the temporary file until the start_index
            for _ in range(start_index):
                line = original_file.readline()
                if not line:
                    break
                temp_file.write(line)

            # Skip lines from start_index to end_index
            for line_number in range(start_index, end_index):
                if (line_number - start_index) % step == 0:
                    next(original_file, None)
                    num_removed += 1

                else:
                    line = original_file.readline()
                    if not line:
                        break
                    temp_file.write(line)

            # Copy the remaining lines after end_index
            for line in original_file:
                temp_file.write(line)

        # Replace the original file with the temporary file
        os.replace(temp_file_path, self.file_name)
        return num_removed
