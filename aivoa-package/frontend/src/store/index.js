import { configureStore } from '@reduxjs/toolkit'

import aiReducer from './aiSlice'
import complaintReducer from './complaintSlice'

export const store = configureStore({
  reducer: {
    complaint: complaintReducer,
    ai: aiReducer,
  },
  middleware: (getDefault) =>
    // File objects are passed to the extraction thunk and are not serialisable.
    getDefault({ serializableCheck: { ignoredActionPaths: ['meta.arg.file'] } }),
})
